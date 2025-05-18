import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  PutCommand,
  QueryCommand,
} from "@aws-sdk/lib-dynamodb";
import bcrypt from "bcryptjs";
import { v4 as uuidv4 } from "uuid";

const client = new DynamoDBClient({});
const ddbDocClient = DynamoDBDocumentClient.from(client);
const USERS_TABLE = "users";

export async function handler(event) {
  try {
    const body = JSON.parse(event.body);
    const { name, email, password } = body;

    if (!name || !email || !password) {
      return response(400, "Missing name, email or password");
    }

    // Check if email already exists
    const existingUser = await ddbDocClient.send(
      new QueryCommand({
        TableName: USERS_TABLE,
        IndexName: "EmailIndex",
        KeyConditionExpression: "email = :email",
        ExpressionAttributeValues: {
          ":email": email,
        },
      })
    );

    if (existingUser.Count > 0) {
      return response(409, "Email already registered");
    }

    const userId = uuidv4();
    const passwordHash = bcrypt.hashSync(password, 10);

    const userItem = {
      userId,
      name,
      email,
      passwordHash,
      role: "user",
      createdAt: new Date().toISOString(),
      isActive: true,
    };

    await ddbDocClient.send(
      new PutCommand({
        TableName: USERS_TABLE,
        Item: userItem,
      })
    );
    console.log("User registered successfully");
    return response(201, "User registered successfully", { userId });
  } catch (err) {
    console.error(err);
    return response(500, `Internal server error: ${err.message}`);
  }
}

function response(statusCode, message, data = {}) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, ...data }),
  };
}
