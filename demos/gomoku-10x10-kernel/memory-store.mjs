import fs from "node:fs";
import path from "node:path";

function defaultMemory(agentName) {
  return {
    agentName,
    games: 0,
    wins: 0,
    losses: 0,
    draws: 0,
    hotMoves: {},
    recentResults: [],
  };
}

export class JsonMemoryStore {
  constructor(baseDir) {
    this.baseDir = baseDir;
    this.cache = new Map();
    fs.mkdirSync(this.baseDir, { recursive: true });
  }

  filePath(agentName) {
    return path.join(this.baseDir, `${agentName}.json`);
  }

  load(agentName) {
    if (this.cache.has(agentName)) {
      return this.cache.get(agentName);
    }

    const file = this.filePath(agentName);
    let data = defaultMemory(agentName);
    if (fs.existsSync(file)) {
      try {
        const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
        data = { ...data, ...parsed };
      } catch {
        data = defaultMemory(agentName);
      }
    }
    this.cache.set(agentName, data);
    return data;
  }

  save(agentName) {
    const data = this.load(agentName);
    fs.writeFileSync(this.filePath(agentName), JSON.stringify(data, null, 2));
  }

  recordMove(agentName, row, col) {
    const data = this.load(agentName);
    const key = `${row},${col}`;
    data.hotMoves[key] = (data.hotMoves[key] || 0) + 1;
    this.save(agentName);
  }

  recordGame(agentName, result) {
    const data = this.load(agentName);
    data.games += 1;
    if (result === "win") data.wins += 1;
    if (result === "loss") data.losses += 1;
    if (result === "draw") data.draws += 1;

    data.recentResults.push(result);
    if (data.recentResults.length > 10) {
      data.recentResults = data.recentResults.slice(-10);
    }
    this.save(agentName);
  }

  getProfile(agentName) {
    const data = this.load(agentName);
    const games = Math.max(1, data.games);
    return {
      ...data,
      winRate: data.wins / games,
    };
  }
}

