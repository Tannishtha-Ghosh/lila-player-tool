import { useEffect, useState, useRef } from "react";
import axios from "axios";

function App() {
  const [matches, setMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState("");
  const [matchData, setMatchData] = useState(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showBots, setShowBots] = useState(true);
  const [showMovement, setShowMovement] = useState(true);
  const [showEvents, setShowEvents] = useState(true);

  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  const API_BASE = "http://127.0.0.1:8000";

  // Load matches
  useEffect(() => {
    axios.get(`${API_BASE}/matches`)
      .then(res => setMatches(res.data))
      .catch(err => console.error(err));
  }, []);

  // Load match
  const loadMatch = (matchId) => {
    setSelectedMatch(matchId);
    axios.get(`${API_BASE}/match/${matchId}`)
      .then(res => {
        setMatchData(res.data);
        setCurrentTime(0);
        setIsPlaying(false);
      })
      .catch(err => console.error(err));
  };

  // Autoplay logic
  useEffect(() => {
    if (!isPlaying || !matchData) return;

    animationRef.current = setInterval(() => {
      setCurrentTime(prev => {
        if (prev >= matchData.duration) {
          setIsPlaying(false);
          return matchData.duration;
        }
        return prev + 0.01;
      });
    }, 30);

    return () => clearInterval(animationRef.current);
  }, [isPlaying, matchData]);

  // Drawing
  useEffect(() => {
    if (!matchData) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    const img = new Image();
    const ext = matchData.map === "Lockdown" ? "jpg" : "png";
    img.src = `/minimaps/${matchData.map}_Minimap.${ext}`;

    img.onload = () => {
      ctx.clearRect(0, 0, 1024, 1024);
      ctx.drawImage(img, 0, 0, 1024, 1024);

      // Heatmap
      if (showHeatmap) {
        matchData.players.forEach(player => {
          if (!showBots && player.is_bot) return;

          player.events.forEach(event => {
            if (event.type.includes("Position") && event.time <= currentTime) {
              const gradient = ctx.createRadialGradient(
                event.x, event.y, 0,
                event.x, event.y, 20
              );
              gradient.addColorStop(0, "rgba(255,0,0,0.3)");
              gradient.addColorStop(1, "rgba(255,0,0,0)");

              ctx.fillStyle = gradient;
              ctx.beginPath();
              ctx.arc(event.x, event.y, 20, 0, 2 * Math.PI);
              ctx.fill();
            }
          });
        });
      }

      matchData.players.forEach(player => {
        if (!showBots && player.is_bot) return;

        // Movement
        if (showMovement) {
          ctx.strokeStyle = player.is_bot ? "#888" : "#ffffff";
          ctx.lineWidth = 1;
          ctx.beginPath();

          let started = false;

          player.events.forEach(event => {
            if (event.type.includes("Position") && event.time <= currentTime) {
              if (!started) {
                ctx.moveTo(event.x, event.y);
                started = true;
              } else {
                ctx.lineTo(event.x, event.y);
              }
            }
          });

          ctx.stroke();
        }

        // Events
        if (showEvents) {
          player.events.forEach(event => {
            if (!event.type.includes("Position") && event.time <= currentTime) {

              let color = "yellow";

              if (event.type === "Kill" || event.type === "BotKill")
                color = "red";

              if (event.type === "Killed" || event.type === "BotKilled")
                color = "black";

              if (event.type === "Loot")
                color = "lime";

              if (event.type === "KilledByStorm")
                color = "purple";

              ctx.beginPath();
              ctx.arc(event.x, event.y, 5, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }
          });
        }
      });
    };

  }, [matchData, currentTime, showHeatmap, showBots, showMovement, showEvents]);

  return (
    <div style={{
      padding: "30px",
      fontFamily: "Inter, sans-serif",
      background: "#121212",
      minHeight: "100vh",
      color: "white"
    }}>

      <h1 style={{ marginBottom: "20px" }}>
        LILA Player Journey Tool
      </h1>

      <select
        value={selectedMatch}
        onChange={(e) => loadMatch(e.target.value)}
        style={{ padding: "8px", marginBottom: "20px", width: "400px" }}
      >
        <option value="">Select Match</option>
        {matches.map((match) => (
          <option key={match.match_id} value={match.match_id}>
            {match.date} - {match.match_id} ({match.player_count} players)
          </option>
        ))}
      </select>

      {matchData && (
        <>
          <h2>Map: {matchData.map}</h2>
          <p>Duration: {matchData.duration.toFixed(2)} seconds</p>

          {/* Timeline */}
          <div style={{ marginBottom: "15px" }}>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              style={{ marginRight: "10px", padding: "6px 12px" }}
            >
              {isPlaying ? "Pause" : "Play"}
            </button>

            <input
              type="range"
              min="0"
              max={matchData.duration}
              step="0.01"
              value={currentTime}
              onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
              style={{ width: "500px" }}
            />
            <span style={{ marginLeft: "10px" }}>
              {currentTime.toFixed(2)}s
            </span>
          </div>

          {/* Filters */}
          <div style={{ marginBottom: "15px" }}>
            <label style={{ marginRight: "15px" }}>
              <input type="checkbox" checked={showBots} onChange={() => setShowBots(!showBots)} /> Show Bots
            </label>

            <label style={{ marginRight: "15px" }}>
              <input type="checkbox" checked={showMovement} onChange={() => setShowMovement(!showMovement)} /> Show Movement
            </label>

            <label style={{ marginRight: "15px" }}>
              <input type="checkbox" checked={showEvents} onChange={() => setShowEvents(!showEvents)} /> Show Events
            </label>

            <label>
              <input type="checkbox" checked={showHeatmap} onChange={() => setShowHeatmap(!showHeatmap)} /> Heatmap
            </label>
          </div>

          {/* Legend */}
          <div style={{ marginBottom: "15px", fontSize: "14px", opacity: 0.8 }}>
            <span style={{ marginRight: "15px" }}>⚪ Human Path</span>
            <span style={{ marginRight: "15px" }}>⚫ Bot Path</span>
            <span style={{ marginRight: "15px" }}>🔴 Kill</span>
            <span style={{ marginRight: "15px" }}>🟢 Loot</span>
            <span style={{ marginRight: "15px" }}>🟣 Storm</span>
            <span>🔥 Heatmap</span>
          </div>

          {/* Canvas */}
          <div style={{ display: "flex", justifyContent: "center" }}>
            <canvas
              ref={canvasRef}
              width={1024}
              height={1024}
              style={{
                border: "1px solid #333",
                boxShadow: "0 0 20px rgba(0,0,0,0.5)"
              }}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default App;