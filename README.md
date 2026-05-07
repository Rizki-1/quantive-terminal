# Quantive Terminal

Self-hosted signal executor for automated crypto trading.

Connect to [dash.quantive.my.id](https://dash.quantive.my.id) to receive trading signals from ML-powered strategies (BTC/ETH 1H), then auto-execute them on your own exchange account.

**Your API keys never leave your server.**

## Quick Start

```bash
git clone <repo-url> quantive-terminal
cd quantive-terminal
pip install -e .
cp config.example.env .env
```

### Option 1: Setup Wizard (Recommended)

```bash
quantive-terminal setup
```

Interactive wizard guides you through:
1. License activation (or 3-day free trial)
2. Exchange API key configuration
3. Telegram notification setup (optional)
4. Model selection & risk per trade
5. Save to `.env`

### Option 2: Manual Config

Edit `.env` with your details, then:

```bash
quantive-terminal test     # Verify connection
quantive-terminal run      # Start trading
```

## Requirements

- Python 3.11+
- Binance/Bybit account with API keys (**withdraw DISABLED**)
- Telegram bot token (optional, for notifications)

## Commands

| Command | Description |
|---------|-------------|
| `quantive-terminal setup` | Interactive setup wizard |
| `quantive-terminal test` | Pre-flight connection check |
| `quantive-terminal run` | Start signal listener + executor |
| `quantive-terminal status` | Show open positions |

## Available Models

| Model | TP | SL | RR | Tier |
|-------|----|----|----|------|
| BTC V1 — ML HHHL | 3.0% | 3.0% | 1:1 | Free |
| BTC V2 — Pivot Filter | 3.0% | 3.0% | 1:1 | Pro |
| BTC V3 — Dow Theory | 3.0% | 3.0% | 1:1 | Pro |
| BTC V3 RR2 — Dow 1:2 | 3.0% | 1.5% | 1:2 | VIP |
| ETH V1 — ML HHHL | 3.0% | 3.0% | 1:1 | Free |
| ETH V2 — Pivot Filter | 3.0% | 3.0% | 1:1 | Pro |

## VPS Deployment

```bash
sudo cp systemd/quantive-terminal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now quantive-terminal
sudo journalctl -u quantive-terminal -f
```

## Docker

```bash
docker compose up -d
docker compose logs -f
```

## Security

- Exchange API keys stored locally in `.env`
- Withdraw MUST be disabled on API key
- TLS for all API communications
- Signal idempotency (dedup by signal_id)
- Orphan position reconciliation on restart

## Disclaimer

Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. You are solely responsible for your trading decisions.
