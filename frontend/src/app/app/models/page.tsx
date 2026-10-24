"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, IconButton, Snackbar,
  Stack, TextField, Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import HubIcon from "@mui/icons-material/Hub";
import NavBar from "../../../components/NavBar";
import { useAuth } from "../../../components/AuthProvider";
import { I18nProvider, useT } from "../../i18n";

interface Preset {
  id: string;
  label: string;
  base_url: string;
  default_model: string;
}

interface CustomModel {
  id: string;
  name: string;
  model: string;
  base_url: string;
  has_key: boolean;
  api_key_masked: string;
  json_mode: boolean;
}

interface Settings {
  active: string;
  providers: Record<string, { base_url: string; model: string; api_key_masked: string; has_key: boolean }>;
  customs: CustomModel[];
}

/** 从 localStorage / cookie 取出令牌，供带鉴权的请求复用。 */
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

function ModelsView() {
  const { t, tf } = useT();
  const { user, loading } = useAuth();
  const [presets, setPresets] = useState<Preset[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [active, setActive] = useState("");
  const [keys, setKeys] = useState<Record<string, string>>({});     // 内置预设密钥输入
  const [models, setModels] = useState<Record<string, string>>({}); // 内置预设模型名
  const [urls, setUrls] = useState<Record<string, string>>({});     // 内置预设 base_url
  const [customName, setCustomName] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [customUrl, setCustomUrl] = useState("");
  const [customKey, setCustomKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [testing, setTesting] = useState<string>("");
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; msg: string } | null>(null);

  const load = useCallback(async () => {
    const p = await api<{ presets: Preset[] }>("/py/v1/llm/presets");
    setPresets(p.presets);
    const s = await api<{ settings: Settings }>("/py/v1/llm/settings");
    setSettings(s.settings);
    setActive(s.settings.active || "");
    const k: Record<string, string> = {};
    const m: Record<string, string> = {};
    const u: Record<string, string> = {};
    for (const [pid, over] of Object.entries(s.settings.providers || {})) {
      m[pid] = over.model || "";
      u[pid] = over.base_url || "";
    }
    for (const pr of p.presets) {
      if (!m[pr.id]) m[pr.id] = pr.default_model;
      if (!u[pr.id]) u[pr.id] = pr.base_url;
    }
    setKeys(k);
    setModels(m);
    setUrls(u);
  }, []);

  useEffect(() => {
    if (user) load().catch((e) => setToast(e.message));
  }, [user, load]);

  async function save(nextActive = active) {
    setSaving(true);
    try {
      const providers: Record<string, { api_key?: string; model?: string; base_url?: string }> = {};
      for (const pr of presets) {
        providers[pr.id] = {
          model: models[pr.id] || pr.default_model,
          base_url: urls[pr.id] || pr.base_url,
        };
        if (keys[pr.id]) providers[pr.id].api_key = keys[pr.id];
      }
      const res = await api<{ settings: Settings }>("/py/v1/llm/settings", {
        method: "PUT",
        body: JSON.stringify({ active: nextActive, providers }),
      });
      setSettings(res.settings);
      setActive(res.settings.active || "");
      setKeys({});
      setToast(t("modelsSaved"));
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function addCustom() {
    try {
      await api("/py/v1/llm/custom", {
        method: "POST",
        body: JSON.stringify({
          name: customName || customModel,
          model: customModel,
          base_url: customUrl,
          api_key: customKey,
        }),
      });
      setCustomName("");
      setCustomModel("");
      setCustomUrl("");
      setCustomKey("");
      setToast(t("modelsAdded"));
      await load();
    } catch (e: any) {
      setToast(e.message);
    }
  }

  async function removeCustom(id: string) {
    try {
      await api(`/py/v1/llm/custom/${id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setToast(e.message);
    }
  }

  async function test(id: string, payload: object) {
    setTesting(id);
    setTestResult(null);
    try {
      const r = await api<{ ok: boolean; error?: string; model?: string }>("/py/v1/llm/test", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setTestResult({
        id,
        ok: r.ok,
        msg: r.ok ? tf("modelsConnected", { model: r.model || "" }) : r.error || t("failed"),
      });
    } catch (e: any) {
      setTestResult({ id, ok: false, msg: e.message });
    } finally {
      setTesting("");
    }
  }

  if (loading) return null;

  return (
    <>
      <NavBar />
      <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1100, mx: "auto" }}>
        <Typography variant="h4" fontWeight={800} sx={{ mb: 1 }}>
          {t("modelsTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {t("modelsSubtitle")}
        </Typography>

        <Grid container spacing={2}>
          {presets.map((p) => {
            const over = settings?.providers?.[p.id];
            const selected = active === p.id;
            return (
              <Grid item xs={12} md={6} key={p.id}>
                <Card
                  variant="outlined"
                  sx={{
                    height: "100%",
                    borderColor: selected ? "primary.main" : "divider",
                    borderWidth: selected ? 2 : 1,
                  }}
                >
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <HubIcon sx={{ color: selected ? "primary.main" : "text.secondary" }} />
                        <Box>
                          <Typography variant="subtitle1" fontWeight={700}>{p.label}</Typography>
                          <Typography variant="caption" color="text.secondary">{p.base_url}</Typography>
                        </Box>
                      </Stack>
                      {selected ? (
                        <Chip size="small" color="primary" label={t("modelsActive")} />
                      ) : (
                        <Button size="small" onClick={() => { setActive(p.id); save(p.id); }}>
                          {t("modelsUse")}
                        </Button>
                      )}
                    </Stack>

                    <Stack spacing={2} sx={{ mt: 2.5 }}>
                      <TextField
                        size="small" label={t("modelsModelName")} value={models[p.id] || p.default_model}
                        onChange={(e) => setModels({ ...models, [p.id]: e.target.value })}
                        fullWidth
                      />
                      <TextField
                        size="small" label={t("modelsBaseUrl")} value={urls[p.id] || p.base_url}
                        onChange={(e) => setUrls({ ...urls, [p.id]: e.target.value })}
                        fullWidth
                      />
                      <TextField
                        size="small" label={t("modelsApiKey")} type="password"
                        placeholder={over?.has_key ? tf("modelsSavedKey", { mask: over.api_key_masked }) : "sk-…"}
                        value={keys[p.id] || ""}
                        onChange={(e) => setKeys({ ...keys, [p.id]: e.target.value })}
                        fullWidth
                      />
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small" variant="outlined"
                          disabled={testing === p.id}
                          onClick={() => test(p.id, {
                            provider: p.id,
                            base_url: urls[p.id] || p.base_url,
                            model: models[p.id] || p.default_model,
                            api_key: keys[p.id] || "",
                          })}
                        >
                          {testing === p.id ? t("modelsTesting") : t("modelsTest")}
                        </Button>
                        <Button size="small" variant="contained" disabled={saving}
                          onClick={() => save(p.id)}>
                          {t("modelsSaveActivate")}
                        </Button>
                      </Stack>
                      {testResult?.id === p.id && (
                        <Alert severity={testResult.ok ? "success" : "error"}>{testResult.msg}</Alert>
                      )}
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>

        <Divider sx={{ my: 5 }} />

        <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
          {t("modelsCustomTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {t("modelsCustomSub")}
        </Typography>

        {(settings?.customs || []).map((c) => (
          <Card
            key={c.id} variant="outlined"
            sx={{ mb: 2, borderColor: active === c.id ? "primary.main" : "divider" }}
          >
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="subtitle1" fontWeight={700}>{c.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {c.model} · {c.base_url} · {c.has_key ? c.api_key_masked : t("modelsNoKey")}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  {active === c.id && <Chip size="small" color="primary" label={t("modelsActive")} />}
                  <Button size="small" disabled={testing === c.id}
                    onClick={() => test(c.id, { custom_id: c.id, base_url: c.base_url, model: c.model, api_key: "" })}>
                    {testing === c.id ? t("modelsTesting") : t("modelsTest")}
                  </Button>
                  <Button size="small" onClick={() => {
                    setActive(c.id);
                    api("/py/v1/llm/settings", {
                      method: "PUT", body: JSON.stringify({ active: c.id }),
                    }).then(load).catch((e) => setToast(e.message));
                  }}>
                    {t("modelsUse")}
                  </Button>
                  <IconButton size="small" onClick={() => removeCustom(c.id)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Stack>
              </Stack>
              {testResult?.id === c.id && (
                <Alert sx={{ mt: 2 }} severity={testResult.ok ? "success" : "error"}>{testResult.msg}</Alert>
              )}
            </CardContent>
          </Card>
        ))}

        <Card variant="outlined">
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <TextField size="small" label={t("modelsDisplayName")} value={customName} fullWidth
                  onChange={(e) => setCustomName(e.target.value)} />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField size="small" label={t("modelsModelName")} value={customModel} fullWidth
                  placeholder={t("modelsPhModel")}
                  onChange={(e) => setCustomModel(e.target.value)} />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField size="small" label={t("modelsBaseUrl")} value={customUrl} fullWidth
                  placeholder={t("modelsPhUrl")}
                  onChange={(e) => setCustomUrl(e.target.value)} />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField size="small" label={t("modelsApiKey")} type="password" value={customKey} fullWidth
                  onChange={(e) => setCustomKey(e.target.value)} />
              </Grid>
            </Grid>
            <Button sx={{ mt: 2 }} variant="contained"
              disabled={!customModel || !customUrl} onClick={addCustom}>
              {t("modelsAddCustom")}
            </Button>
          </CardContent>
        </Card>

        {!presets.length && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
            {t("modelsNoPresets")}
          </Typography>
        )}

        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 4 }}>
          <CheckCircleIcon fontSize="small" sx={{ color: "success.main" }} />
          <Typography variant="caption" color="text.secondary">
            {t("modelsApplied")}
          </Typography>
        </Stack>
      </Box>

      <Snackbar
        open={Boolean(toast)} autoHideDuration={4000} onClose={() => setToast("")}
        message={toast}
      />
    </>
  );
}

export default function ModelsPage() {
  return (
    <I18nProvider>
      <ModelsView />
    </I18nProvider>
  );
}
