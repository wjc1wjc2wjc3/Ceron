"use client";

import { useEffect, useRef, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, Paper, Stack, TextField, Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import SendIcon from "@mui/icons-material/Send";
import NavBar from "../../../components/NavBar";
import { I18nProvider, useT } from "../../i18n";

interface Citation {
  id: string;
  source: string;
  title: string;
  text: string;
}

interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  result_summary: string;
}

interface Turn {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  tool_calls?: ToolCall[];
}

function token(): string {
  if (typeof document === "undefined") return "";
  return localStorage.getItem("ceron_token") || "";
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token()}`,
      ...(init?.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || data?.error || `request_failed_${res.status}`);
  return data as T;
}

const VERTICALS = [
  "insurance_hk", "trust", "family_office",
  "banking_mortgage", "securities_suitability", "mpf", "fund_ofc_lpf",
];

function AgentView() {
  const { t } = useT();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [vertical, setVertical] = useState(VERTICALS[0]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setBusy(true);
    setError("");
    setTurns((prev) => [...prev, { role: "user", content: msg }]);
    setInput("");
    try {
      const r = await api<{
        session_id: string; answer: string; citations: Citation[]; tool_calls: ToolCall[];
      }>("/py/v1/agent/chat", {
        method: "POST",
        body: JSON.stringify({ message: msg, session_id: sessionId || null, vertical }),
      });
      setSessionId(r.session_id);
      setTurns((prev) => [...prev, {
        role: "assistant",
        content: r.answer,
        citations: r.citations || [],
        tool_calls: r.tool_calls || [],
      }]);
    } catch (e: any) {
      setError(e.message);
      setTurns((prev) => [...prev, { role: "assistant", content: `（${e.message}）` }]);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setTurns([]);
    setSessionId("");
    setError("");
  }

  return (
    <>
      <NavBar />
      <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1000, mx: "auto" }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }}>
          <Typography variant="h4" fontWeight={800}>{t("agentTitle")}</Typography>
          <Button size="small" onClick={reset} disabled={!turns.length}>{t("agentNewSession")}</Button>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {t("agentSubtitle")}
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={6}>
            <TextField
              select size="small" fullWidth label={t("agentVertical")} value={vertical}
              onChange={(e) => setVertical(e.target.value)}
              SelectProps={{ native: true }}
            >
              {VERTICALS.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} md={6} sx={{ display: "flex", alignItems: "center" }}>
            <Chip
              icon={<AutoAwesomeIcon />} size="small"
              color={sessionId ? "primary" : "default"}
              label={sessionId ? `${t("agentSession")}: ${sessionId}` : t("agentNoSession")}
            />
          </Grid>
        </Grid>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Paper variant="outlined" sx={{ p: 2, minHeight: 380, maxHeight: 560, overflowY: "auto" }}>
          {!turns.length && (
            <Typography variant="body2" color="text.secondary">
              {t("agentEmpty")}
            </Typography>
          )}
          <Stack spacing={2}>
            {turns.map((turn, i) => (
              <Box key={i}>
                <Typography variant="caption" color="text.secondary" fontWeight={700}>
                  {turn.role === "user" ? t("agentYou") : t("agentBot")}
                </Typography>
                <Paper
                  elevation={0}
                  sx={{
                    p: 1.5, mt: 0.5, whiteSpace: "pre-wrap",
                    bgcolor: turn.role === "user" ? "action.hover" : "transparent",
                    border: 1, borderColor: "divider", borderRadius: 2,
                  }}
                >
                  <Typography variant="body2">{turn.content}</Typography>
                </Paper>

                {turn.tool_calls && turn.tool_calls.length > 0 && (
                  <Stack direction="row" spacing={0.5} sx={{ mt: 1, flexWrap: "wrap", gap: 0.5 }}>
                    {turn.tool_calls.map((tc, j) => (
                      <Chip
                        key={j} size="small" variant="outlined"
                        label={`${t("agentTool")}: ${tc.tool}`}
                        title={tc.result_summary}
                      />
                    ))}
                  </Stack>
                )}

                {!!turn.citations?.length && (
                  <Card variant="outlined" sx={{ mt: 1.5 }}>
                    <CardContent>
                      <Typography variant="caption" color="text.secondary" fontWeight={700}>
                        {t("agentCitations")}
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                      <Stack spacing={1}>
                        {turn.citations.map((c) => (
                          <Box key={c.id}>
                            <Typography variant="body2" fontWeight={600}>
                              [{c.id}] {c.source} · {c.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {c.text}
                            </Typography>
                          </Box>
                        ))}
                      </Stack>
                    </CardContent>
                  </Card>
                )}
              </Box>
            ))}
            <div ref={bottomRef} />
          </Stack>
        </Paper>

        <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
          <TextField
            fullWidth multiline maxRows={4} size="small"
            label={t("agentPlaceholder")} value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <Button
            variant="contained" disabled={busy || !input.trim()} onClick={send}
            startIcon={<SendIcon />} sx={{ px: 3, whiteSpace: "nowrap" }}
          >
            {busy ? t("agentThinking") : t("agentSend")}
          </Button>
        </Stack>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
          {t("agentDisclaimer")}
        </Typography>
      </Box>
    </>
  );
}

export default function AgentPage() {
  return (
    <I18nProvider>
      <AgentView />
    </I18nProvider>
  );
}
