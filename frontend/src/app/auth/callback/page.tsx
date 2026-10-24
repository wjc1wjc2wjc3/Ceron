"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";
import { useAuth } from "../../../components/AuthProvider";

/** X / Facebook 登录后回跳到此页：用 URL 上的 token 建立会话，再进入控制台。 */
function CallbackInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { setToken } = useAuth();
  const [error, setError] = useState("");
  const handled = useRef(false);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("missing_token");
      return;
    }
    if (handled.current) return;
    handled.current = true;
    setToken(token)
      .then(() => router.replace("/app"))
      .catch((e: any) => setError(e?.message || "callback_failed"));
  }, [params, router, setToken]);

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Stack spacing={2} alignItems="center">
        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <>
            <CircularProgress size={26} />
            <Typography variant="body2" color="text.secondary">
              Signing you in…
            </Typography>
          </>
        )}
      </Stack>
    </Box>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<Box sx={{ minHeight: "100vh" }} />}>
      <CallbackInner />
    </Suspense>
  );
}
