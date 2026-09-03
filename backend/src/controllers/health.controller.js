/**
 * Health check controller.
 * Reports gateway health, database connectivity, and environment mode safely.
 */

const { getConnectionStatus } = require('../config/database');
const { NODE_ENV } = require('../config/env');

const getHealth = (_req, res) => {
  const dbStatus = getConnectionStatus();

  res.status(200).json({
    success: true,
    service: 'nyayasetu-backend',
    status: 'healthy',
    environment: NODE_ENV,
    timestamp: new Date().toISOString(),
    database: {
      connected: dbStatus.connected,
      status: dbStatus.state,
      name: dbStatus.dbName,
    },
  });
};

module.exports = { getHealth };
