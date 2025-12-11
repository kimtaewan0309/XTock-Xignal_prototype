"use client";
import { useState } from "react";
import api from "../utils/api"; 
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';

export default function HistoricalImpactSection() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if(!query) return;
    setLoading(true);
    setResult(null);
    
    try {
      const res = await api.post("/api/historical-impact", { text: query });
      if(res.data.found) {
        setResult(res.data);
      } else {
        alert(res.data.msg || "분석 결과를 찾을 수 없습니다.");
      }
    } catch(e) {
      console.error(e);
      alert("데이터 분석 중 오류가 발생했습니다.");
    }
    setLoading(false);
  };

  // 차트 툴팁
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-800 border border-slate-600 p-2 rounded shadow-lg text-xs text-white">
          <p className="font-bold mb-1">{label}</p>
          <p>주가: ${payload[0].value.toFixed(2)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* 1. 검색창 */}
      <div className="flex flex-col items-center justify-center space-y-4 py-10 bg-slate-900/50 rounded-2xl border border-slate-800">
        <h2 className="text-2xl font-bold text-white">과거 트윗 영향력 분석 (AI)</h2>
        <p className="text-slate-400 text-sm">"Elon Musk", "Twitter Deal", "Battery Day" 등 키워드로 AI 분석을 시작하세요.</p>
        
        <div className="flex gap-3 w-full max-w-xl">
          <input 
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            placeholder="검색어 입력 (예: Elon Musk)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key==='Enter' && handleSearch()}
          />
          <button 
            onClick={handleSearch} 
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-xl font-bold transition-colors disabled:opacity-50"
          >
            {loading ? "분석 중..." : "분석 시작"}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* 2. AI 분석 결과 요약 */}
          <div className="bg-indigo-900/20 border border-indigo-500/30 rounded-xl p-4 text-center">
            <span className="text-indigo-400 font-semibold">AI 분석 결과: </span>
            <span className="text-slate-200 ml-2">
              "{query}" 키워드와 가장 유사한 과거 사건(Event)을 찾았습니다.
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 3. 트윗 정보 카드 */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl shadow-lg">
                    {result.event.symbol ? result.event.symbol.charAt(0) : "E"}
                  </div>
                  <div>
                    <div className="font-bold text-white text-lg">{result.event.author_id}</div>
                    <div className="text-slate-400 text-sm">{result.event.created_at}</div>
                  </div>
                </div>
                <div className="relative">
                  <span className="absolute -top-3 -left-2 text-4xl text-slate-700">"</span>
                  <p className="text-slate-100 text-xl leading-relaxed font-serif italic pl-6 mb-8 relative z-10">
                    {result.event.text}
                  </p>
                </div>
              </div>

              {/* 수익률 표시 */}
              <div className="bg-slate-800 rounded-xl p-5 flex justify-between items-center border border-slate-700">
                <span className="text-slate-400 font-medium">이벤트 발생 후 +5일 수익률</span>
                <span className={`text-3xl font-extrabold ${result.impact_return >= 0 ? 'text-red-500' : 'text-blue-500'}`}>
                  {result.impact_return > 0 ? "+" : ""}{result.impact_return.toFixed(2)}%
                </span>
              </div>
            </div>

            {/* 4. 과거 차트 (Recharts 적용) */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 h-[400px] flex flex-col">
              <h3 className="text-lg font-bold text-white mb-4">당시 주가 변동 추이</h3>
              <div className="flex-1 w-full">
                {result.stock_data && result.stock_data.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={result.stock_data}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke="#94a3b8" 
                        tick={{fontSize: 11}}
                        tickFormatter={(val) => val.substring(5)} 
                        interval="preserveStartEnd"
                      />
                      <YAxis domain={['auto', 'auto']} stroke="#94a3b8" width={50} />
                      <Tooltip content={<CustomTooltip />} />
                      
                      {/* 이벤트 발생 시점 표시선 */}
                      {result.post_index >= 0 && result.stock_data[result.post_index] && (
                        <ReferenceLine 
                          x={result.stock_data[result.post_index].date} 
                          stroke="#fbbf24" 
                          strokeDasharray="3 3"
                          label={{ position: 'top', value: 'Event', fill: '#fbbf24', fontSize: 12 }} 
                        />
                      )}

                      <Line 
                        type="monotone" 
                        dataKey="price" 
                        stroke="#6366f1" 
                        strokeWidth={3} 
                        dot={false}
                        activeDot={{r: 6}}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500">
                    차트 데이터를 불러올 수 없습니다.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}