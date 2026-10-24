"use client";

import { useEffect, useState } from "react";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";

export default function Home() {
  const [health, setHealth] = useState<any>(null);
  const [vertical, setVertical] = useState("insurance_hk");
  const [text, setText] = useState(
    "投保人：香港環宇保險有限公司\n保單號：HK12345\n受保人：張三\n險種：終身壽險\n保額：800萬\n年繳保費：20萬\n理賠類型：身故\n理賠金額：120萬\n資料完整度：0.9"
  );
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "error" }));
  }, []);

  async function submit() {
    const res = await fetch("/api/v1/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vertical, text }),
    });
    setResult(await res.json());
  }

  return (
    <Box sx={{ p: 4, maxWidth: 800, mx: "auto" }}>
      <Typography variant="h4" gutterBottom>
        Ceron 控制台
      </Typography>
      <Typography sx={{ mb: 2 }}>网关状态：{JSON.stringify(health)}</Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <TextField
          label="垂直场景"
          value={vertical}
          onChange={(e) => setVertical(e.target.value)}
          fullWidth
          sx={{ mb: 2 }}
        />
        <TextField
          label="文档文本"
          value={text}
          onChange={(e) => setText(e.target.value)}
          multiline
          minRows={6}
          fullWidth
          sx={{ mb: 2 }}
        />
        <Button variant="contained" onClick={submit}>
          提交并编排
        </Button>
      </Paper>

      {result && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6">处理结果</Typography>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </Paper>
      )}
    </Box>
  );
}
