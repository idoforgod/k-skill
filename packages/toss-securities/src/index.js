const childProcess = require("node:child_process");
const util = require("node:util");

const {
  buildReadOnlyArgs,
  parseJsonOutput
} = require("./parse");

const execFile = util.promisify(childProcess.execFile);

function buildReadOnlyCommand(commandName, options = {}) {
  return {
    bin: options.bin || "tossctl",
    args: buildReadOnlyArgs(commandName, options)
  };
}

async function runReadOnlyCommand(commandName, options = {}) {
  const command = buildReadOnlyCommand(commandName, options);

  try {
    const result = await execFile(command.bin, command.args, {
      cwd: options.cwd,
      env: options.env,
      timeout: options.timeoutMs,
      maxBuffer: options.maxBuffer || 1024 * 1024
    });

    return {
      ...command,
      ...parseJsonOutput(result.stdout, commandName),
      stderr: result.stderr
    };
  } catch (error) {
    const stderr = String(error.stderr || "").trim();
    const detail = stderr || error.message;

    throw new Error(`tossctl ${commandName} failed: ${detail}`, {
      cause: error
    });
  }
}

function listAccounts(options = {}) {
  return runReadOnlyCommand("accountList", options);
}

function getAccountSummary(options = {}) {
  return runReadOnlyCommand("accountSummary", options);
}

function getPortfolioPositions(options = {}) {
  return runReadOnlyCommand("portfolioPositions", options);
}

function getPortfolioAllocation(options = {}) {
  return runReadOnlyCommand("portfolioAllocation", options);
}

function listOrders(options = {}) {
  return runReadOnlyCommand("ordersList", options);
}

function listCompletedOrders(options = {}) {
  return runReadOnlyCommand("ordersCompleted", options);
}

function listWatchlist(options = {}) {
  return runReadOnlyCommand("watchlistList", options);
}

function getQuote(symbol, options = {}) {
  return runReadOnlyCommand("quoteGet", {
    ...options,
    symbol
  });
}

function getQuoteBatch(symbols, options = {}) {
  return runReadOnlyCommand("quoteBatch", {
    ...options,
    symbols
  });
}

module.exports = {
  buildReadOnlyCommand,
  getAccountSummary,
  getPortfolioAllocation,
  getPortfolioPositions,
  getQuote,
  getQuoteBatch,
  listAccounts,
  listCompletedOrders,
  listOrders,
  listWatchlist,
  runReadOnlyCommand
};
