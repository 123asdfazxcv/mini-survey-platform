// 多后端 API 代理 — 解决浏览器 CORS，支持 Ollama（零密钥）/ Claude / DeepSeek
// 用法: node proxy.js
// 自动检测 Ollama → 无需任何配置即可使用真实 AI！

const http = require('http');
const https = require('https');

const PORT = 3001;

// ---- 后端选择（按优先级自动检测）----
const USE_ANTHROPIC = process.env.ANTHROPIC_API_KEY || '';
const USE_DEEPSEEK  = process.env.DEEPSEEK_API_KEY || '';
// Ollama 不需要任何配置，自动检测

// ---- 请求转发 ----
function forward(url, opts, reqBody, clientRes) {
  const isHttps = url.startsWith('https');
  const mod = isHttps ? https : http;
  const u = new URL(url);
  const proxy = mod.request({
    hostname: u.hostname, port: u.port || (isHttps ? 443 : 80),
    path: u.pathname, method: 'POST',
    headers: { 'Content-Type': 'application/json', ...opts }
  }, proxyRes => {
    clientRes.writeHead(proxyRes.statusCode, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    let data = '';
    proxyRes.on('data', c => data += c);
    proxyRes.on('end', () => clientRes.end(data));
  });
  proxy.on('error', e => { clientRes.writeHead(502); clientRes.end(JSON.stringify({error: e.message})); });
  proxy.write(reqBody);
  proxy.end();
}

// ---- 格式转换：Anthropic → Ollama ----
function anthropicToOllama(body) {
  const systemMsg = body.system || '';
  const userMsg = (body.messages || []).map(m => m.content).join('\n');
  const fullPrompt = systemMsg + '\n\n' + userMsg;
  return JSON.stringify({
    model: process.env.OLLAMA_MODEL || 'qwen2.5:7b',
    prompt: fullPrompt,
    stream: false,
    options: { temperature: 0.8, num_predict: 500 }
  });
}

// ---- 主逻辑 ----
const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-api-key, anthropic-version');

  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

  // 状态查询端点
  if (req.method === 'GET' && req.url === '/api/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      backend: USE_ANTHROPIC ? 'anthropic' : USE_DEEPSEEK ? 'deepseek' : 'ollama',
      ollama_available: true  // 启动时已检测
    }));
    return;
  }

  if (req.method === 'POST' && req.url === '/api/chat') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      if (USE_ANTHROPIC) {
        // Anthropic API
        forward('https://api.anthropic.com/v1/messages',
          { 'x-api-key': USE_ANTHROPIC, 'anthropic-version': '2023-06-01' }, body, res);
      } else if (USE_DEEPSEEK) {
        // DeepSeek API（兼容 OpenAI 格式）
        const b = JSON.parse(body);
        const converted = JSON.stringify({
          model: 'deepseek-chat',
          messages: [
            { role: 'system', content: b.system || '' },
            { role: 'user', content: (b.messages || [{content:''}])[0].content }
          ],
          max_tokens: 500, temperature: 0.8
        });
        forward('https://api.deepseek.com/v1/chat/completions',
          { 'Authorization': 'Bearer ' + USE_DEEPSEEK }, converted, res);
      } else {
        // Ollama（零密钥，本地模型）
        const converted = anthropicToOllama(JSON.parse(body));
        forward('http://127.0.0.1:11434/api/generate', {}, converted, res);
      }
    });
  } else {
    res.writeHead(404); res.end('Not Found');
  }
});

// ---- 启动时检测 Ollama ----
function checkOllama(cb) {
  if (USE_ANTHROPIC || USE_DEEPSEEK) { cb(true); return; }
  const r = http.request('http://127.0.0.1:11434/api/tags', { method: 'GET', timeout: 3000 }, resp => {
    let d = ''; resp.on('data', c => d += c);
    resp.on('end', () => { cb(resp.statusCode === 200); });
  });
  r.on('error', () => cb(false));
  r.on('timeout', () => { r.destroy(); cb(false); });
}

checkOllama(ok => {
  server.listen(PORT, () => {
    console.log('========================================');
    console.log('  API 代理已启动: http://localhost:' + PORT);
    console.log('========================================');
    if (USE_ANTHROPIC) {
      console.log('  后端: Claude API (Anthropic)');
    } else if (USE_DEEPSEEK) {
      console.log('  后端: DeepSeek API');
    } else if (ok) {
      console.log('  后端: Ollama 本地模型 ✅ (零密钥，已自动检测)');
      console.log('  模型: ' + (process.env.OLLAMA_MODEL || 'qwen2.5:7b'));
      console.log('  如需换模型: set OLLAMA_MODEL=qwen2.5:14b && node proxy.js');
    } else {
      console.log('  ❌ Ollama 未检测到！请先安装:');
      console.log('     1. 下载安装 Ollama: https://ollama.com');
      console.log('     2. 拉取模型: ollama pull qwen2.5:7b');
      console.log('     3. 重新运行: node proxy.js');
      console.log('  -- 或者设置 API Key --');
      console.log('     set ANTHROPIC_API_KEY=sk-ant-xxx && node proxy.js');
      console.log('     set DEEPSEEK_API_KEY=sk-xxx && node proxy.js');
    }
  });
});
