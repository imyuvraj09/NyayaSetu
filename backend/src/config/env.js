/**
 * Environment configuration for NyayaSetu Node.js Backend.
 * Safely parses and validates environment variables with production-ready defaults.
 */

const PORT = parseInt(process.env.PORT, 10) || 3000;
const NODE_ENV = process.env.NODE_ENV || 'development';

// RAG Service Configuration
const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://127.0.0.1:8000';
const RAG_SERVICE_TIMEOUT_MS = parseInt(process.env.RAG_SERVICE_TIMEOUT_MS, 10) || 180000;

// MongoDB Configuration
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/nyayasetu';
const DATABASE_NAME = process.env.DATABASE_NAME || 'nyayasetu';

// Frontend Integration / CORS
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

module.exports = {
  PORT,
  NODE_ENV,
  RAG_SERVICE_URL,
  RAG_SERVICE_TIMEOUT_MS,
  MONGODB_URI,
  DATABASE_NAME,
  FRONTEND_URL,
};
