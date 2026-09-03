/**
 * Express Application initialization for NyayaSetu Backend.
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const { FRONTEND_URL, NODE_ENV } = require('./config/env');
const healthRoutes = require('./routes/health.routes');
const chatRoutes = require('./routes/chat.routes');
const errorHandler = require('./middleware/errorHandler');
const { sendError } = require('./utils/apiResponse');

const app = express();

// --------------- Security & Parsing Middleware ---------------
app.use(helmet());

// CORS configuration (configured for React frontend)
const allowedOrigins = [
  FRONTEND_URL,
  'http://localhost:5173',
  'http://127.0.0.1:5173',
];

app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (like mobile apps, curl, server-to-server)
      if (!origin || allowedOrigins.includes(origin) || NODE_ENV === 'development') {
        return callback(null, true);
      }
      return callback(new Error('CORS policy does not allow access from this origin.'));
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'Accept'],
    credentials: true,
  })
);

// Logging
if (NODE_ENV !== 'test') {
  app.use(morgan(':method :url :status :res[content-length] - :response-time ms'));
}

// Body parsers
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb' }));

// --------------- Routes ---------------
app.use('/api/health', healthRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/chats', chatRoutes);

// --------------- 404 Handler ---------------
app.use((req, res) => {
  return sendError(
    res,
    'ROUTE_NOT_FOUND',
    `The requested endpoint '${req.method} ${req.originalUrl}' does not exist on this server.`,
    404
  );
});

// --------------- Centralized Error Handler ---------------
app.use(errorHandler);

module.exports = app;
