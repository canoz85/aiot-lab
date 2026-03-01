function createMetrics() {
	return {
		startedAt: new Date().toISOString(),
		decisionsReceived: 0,
		invalidMessages: 0,
		lastMessageAt: null,
	};
}

function recordDecision(metrics) {
	metrics.decisionsReceived += 1;
	metrics.lastMessageAt = new Date().toISOString();
}

function recordInvalid(metrics) {
	metrics.invalidMessages += 1;
	metrics.lastMessageAt = new Date().toISOString();
}

module.exports = {
	createMetrics,
	recordDecision,
	recordInvalid,
};

