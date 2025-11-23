#!/usr/bin/env node
import { log } from "./log.mjs";

export async function notifyDiscord({ webhook, title, description = "", color = 3066993 }) {
  if (!webhook) {
    log("debug", "Discord webhook not provided, skipping");
    return;
  }
  const payload = {
    embeds: [
      {
        title,
        description,
        color,
        timestamp: new Date().toISOString(),
      },
    ],
  };
  try {
    const res = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      log("warn", "Discord webhook failed", { status: res.status });
    }
  } catch (err) {
    log("warn", "Discord webhook error", { error: err?.message });
  }
}
