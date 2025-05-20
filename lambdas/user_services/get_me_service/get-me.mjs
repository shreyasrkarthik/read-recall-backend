import { DynamoDBClient, GetItemCommand } from "@aws-sdk/client-dynamodb";
import jwt from "jsonwebtoken";

const client = new DynamoDBClient({});
const USERS_TABLE = "users";

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_ALGORITHM = "HS256";

export async function handler(event) {
  try {
    // Extract and verify JWT
    const token = getTokenFromHeader(event);
    const payload = verifyJwtToken(token);

    const userId = payload.userId;
    if (!userId) {
      return response(401, "Unauthorized: userId not found in token");
    }

    // Fetch user from DynamoDB
    const result = await client.send(
      new GetItemCommand({
        TableName: USERS_TABLE,
        Key: {
          userId: { S: userId },
        },
      })
    );

    if (!result.Item) {
      return response(404, "User not found");
    }

    const user = result.Item;
    const userInfo = {
      userId: user.userId.S,
      name: user.name.S,
      email: user.email.S,
      role: user.role?.S || "user",
      isActive: user.isActive?.BOOL ?? true,
      createdAt: user.createdAt?.S,
    };

    return response(200, "User retrieved successfully", userInfo);
  } catch (err) {
    if (err.name === "TokenExpiredError") {
      return response(401, "Token has expired");
    } else if (err.name === "JsonWebTokenError") {
      return response(401, "Invalid token");
    } else {
      console.error("Unhandled error:", err);
      return response(500, `Internal server error: ${err.message}`);
    }
  }
}

function getTokenFromHeader(event) {
  const headers = event.headers || {};
  const authHeader = headers.Authorization || headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    throw new jwt.JsonWebTokenError("Missing or invalid Authorization header");
  }

  return authHeader.split(" ")[1];
}

function verifyJwtToken(token) {
  return jwt.verify(token, JWT_SECRET, { algorithms: [JWT_ALGORITHM] });
}

function response(statusCode, message, data = {}) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, ...data }),
  };
}
