import { useState, useEffect } from "react";
import type { Color, Move } from "../types";
import "./Board.css";

interface BoardProps {
  rows: number;
  cols: number;
  board: (Color | null)[][];
  moves: Move[];
  onCellClick: (row: number, col: number) => void;
}

function useCellSize(cols: number): number {
  const [cellSize, setCellSize] = useState(28);

  useEffect(() => {
    const calculate = () => {
      const maxWidth = Math.min(window.innerWidth - 24, 600);
      const size = Math.floor(maxWidth / cols);
      setCellSize(Math.max(16, Math.min(size, 36)));
    };
    calculate();
    window.addEventListener("resize", calculate);
    return () => window.removeEventListener("resize", calculate);
  }, [cols]);

  return cellSize;
}

export function Board({ rows, cols, board, moves, onCellClick }: BoardProps) {
  const lastMove = moves.length > 0 ? moves[moves.length - 1] : null;
  const cellSize = useCellSize(cols);

  return (
    <div className="board-container">
      {/* Grid lines layer */}
      <div
        className="board-grid"
        style={{
          gridTemplateColumns: `repeat(${cols - 1}, 1fr)`,
          gridTemplateRows: `repeat(${rows - 1}, 1fr)`,
          width: `${(cols - 1) * cellSize}px`,
          height: `${(rows - 1) * cellSize}px`,
        }}
      >
        {Array.from({ length: (rows - 1) * (cols - 1) }).map((_, i) => (
          <div key={i} className="grid-cell" />
        ))}
      </div>

      {/* Stones layer */}
      <div
        className="board-stones"
        style={{
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridTemplateRows: `repeat(${rows}, 1fr)`,
          width: `${cols * cellSize}px`,
          height: `${rows * cellSize}px`,
        }}
      >
        {board.flatMap((row, r) =>
          row.map((cell, c) => {
            const isLast = lastMove && lastMove.row === r && lastMove.col === c;
            return (
              <div
                key={`${r}-${c}`}
                className={[
                  "stone-cell",
                  cell === "b" ? "black" : cell === "w" ? "white" : "",
                  isLast ? "last-move" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                style={{ width: cellSize, height: cellSize }}
                onClick={() => !cell && onCellClick(r, c)}
              />
            );
          })
        )}
      </div>
    </div>
  );
}
