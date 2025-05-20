import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand } from "@aws-sdk/lib-dynamodb";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";

const client = new DynamoDBClient({});
const ddbDocClient = DynamoDBDocumentClient.from(client);
const USERS_TABLE = "users";

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_ALGORITHM = "HS256";
const JWT_EXP_HOURS = 48;

export async function handler(event) {
  try {
    const body = JSON.parse(event.body);
    const { email, password } = body;

    if (!email || !password) {
      return response(400, "Missing email or password");
    }

    // Query user by email
    const result = await ddbDocClient.send(
      new QueryCommand({
        TableName: USERS_TABLE,
        IndexName: "EmailIndex",
        KeyConditionExpression: "email = :email",
        ExpressionAttributeValues: {
          ":email": email,
        },
      })
    );

    if (result.Count === 0 || result.Items.length === 0) {
      return response(401, "Invalid email or password");
    }

    const user = result.Items[0];

    // Check password
    const passwordValid = bcrypt.compareSync(password, user.passwordHash);
    if (!passwordValid) {
      return response(401, "Invalid email or password");
    }

    // Generate JWT
    const token = generateJWT(user);

    return response(200, "Login successful", {
      token,
      userId: user.user_id || user.userId,
      name: user.name,
      email: user.email,
      role: user.role || "user",
      isActive: user.isActive ?? true,
    });
  } catch (err) {
    console.error(err);
    return response(500, `Internal server error: ${err.message}`);
  }
}

function generateJWT(user) {
  const payload = {
    userId: user.user_id || user.userId,
    email: user.email,
    role: user.role || "user",
    exp: Math.floor(Date.now() / 1000) + JWT_EXP_HOURS * 3600,
  };
  return jwt.sign(payload, JWT_SECRET, { algorithm: JWT_ALGORITHM });
}

function response(statusCode, message, data = {}) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, ...data }),
  };
}
