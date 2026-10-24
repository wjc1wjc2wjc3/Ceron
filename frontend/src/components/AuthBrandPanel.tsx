"use client";

import Link from "next/link";
import { Box, Stack, Typography } from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";

/** 登录/注册共用的左侧品牌面板（深色渐变 + 价值主张）。 */
export default function AuthBrandPanel({ quoteKey, personKey }: { quoteKey: string; personKey: string }) {
  return (
    <Box
      sx={{
        display: { xs: "none", md: "flex" },
        flexDirection: "column",
        justifyContent: "space-between",
        p: 6,
        color: "#fff",
        background: "linear-gradient(160deg,#0b1a3a 0%,#132a63 45%,#1f4dff 100%)",
      }}
    >
      <Stack direction="row" spacing={1.5} alignItems="center">
        <HubIcon />
        <Typography variant="h6" fontWeight={800}>
          Ceron
        </Typography>
      </Stack>

      <Box>
        <Typography variant="h4" sx={{ mb: 3, fontWeight: 700, lineHeight: 1.35 }}>
          “{quoteKey}”
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.8 }}>
          {personKey}
        </Typography>
      </Box>

      <Stack spacing={1.5}>
        {[
          "Intake → Extract → Enrich → Decision",
          "ICRIS · Land Search · Credit bureau · OFAC / HMT · CRS",
          "SFC / HKMA / MPFA compliance gates built in",
        ].map((line) => (
          <Stack key={line} direction="row" spacing={1} alignItems="center">
            <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "#7df0c6" }} />
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {line}
            </Typography>
          </Stack>
        ))}
      </Stack>

      <Typography variant="caption" sx={{ opacity: 0.7 }} component={Link} href="/">
        ← Back to ceron.ai
      </Typography>
    </Box>
  );
}
