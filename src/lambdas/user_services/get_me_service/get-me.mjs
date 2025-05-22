import { DynamoDBClient, GetItemCommand } from "@aws-sdk/client-dynamodb";
import jwt from "jsonwebtoken";

const client = new DynamoDBClient({});
const USERS_TABLE = "users"; // Ensure this matches your actual table name

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_ALGORITHM = "HS256";

export async function handler(event) {
  try {
    // Extract and verify JWT
    const token = getTokenFromHeader(event);
    const payload = verifyJwtToken(token);

    // Ensure payload.userId matches the key name in your JWT payload
    // and correctly extract the ID from the JWT
    const userId = payload.userId; // This refers to the 'userId' property inside the JWT payload
    if (!userId) {
      return response(401, "Unauthorized: userId not found in token");
    }

    // Fetch user from DynamoDB
    const result = await client.send(
      new GetItemCommand({
        TableName: USERS_TABLE,
        Key: {
          // *** CRITICAL CHANGE HERE: Use 'user_id' to match your DynamoDB partition key ***
          user_id: { S: userId }, // Use the 'userId' from the JWT, but map it to 'user_id' in DynamoDB
        },
      })
    );

    if (!result.Item) {
      return response(404, "User not found");
    }

    const user = result.Item;

    // Construct userInfo object, ensuring you access attributes as they are stored in DynamoDB
    const userInfo = {
      // Accessing 'user_id' from the item, as that's what you stored it as
      userId: user.user_id.S, // Use user.user_id.S for the retrieved item's primary key
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
      // Ensure we provide the actual error message for debugging internal errors
      return response(500, `Internal server error: ${err.message}`);
    }
  }
}

function getTokenFromHeader(event) {
  console.log("Received event:", JSON.stringify(event, null, 2));
  const headers = event.headers || {};
  // Handle cases where Authorization header might be capitalized or not
  const authHeader = headers.Authorization || headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    throw new jwt.JsonWebTokenError("Missing or invalid Authorization header");
  }

  return authHeader.split(" ")[1];
}

function verifyJwtToken(token) {
  // Ensure JWT_SECRET is correctly set in Lambda environment variables
  return jwt.verify(token, JWT_SECRET, { algorithms: [JWT_ALGORITHM] });
}

function response(statusCode, message, data = {}) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, ...data }),
  };
}