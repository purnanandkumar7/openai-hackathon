# Atlas AI Frontend

> Next.js 14 frontend for the Atlas AI incident intelligence platform.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v3 + shadcn/ui patterns |
| State | TanStack React Query v5 + Zustand |
| Real-time | WebSocket (native + socket.io-client) |
| Charts | Recharts |
| Icons | Lucide React |

## Project Structure

```
app/
  layout.tsx                 # Root layout with sidebar + header
  page.tsx                   # Dashboard home
  providers.tsx              # React Query provider
  incidents/
    page.tsx                 # Incidents list with filters
    new/page.tsx             # Create new incident
    [id]/
      page.tsx               # Incident detail + live agent feed
      rca/page.tsx           # RCA report viewer
  agents/page.tsx            # Agent dashboard
  learning/page.tsx          # Learning loop metrics
  settings/page.tsx          # Settings

components/
  layout/
    Sidebar.tsx              # Left nav sidebar
    Header.tsx               # Top header with breadcrumbs
  incidents/
    IncidentCard.tsx         # Incident summary card
    AgentProgressFeed.tsx    # Real-time WebSocket agent feed
    RCAReport.tsx            # Full RCA report component
  agents/
    AgentCard.tsx            # Agent status card
  ui/
    SeverityBadge.tsx        # P1/P2/P3/P4 badges
    StatusIndicator.tsx      # Status dots with animation

lib/
  types.ts                   # All TypeScript interfaces
  api.ts                     # API client
  websocket.ts               # WebSocket hook + mock emitter
  mock-data.ts               # Realistic mock data
  utils.ts                   # cn(), formatRelativeTime(), etc.
```

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Type check
npm run type-check
```

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Docker

```bash
# Build
docker build \
  --build-arg NEXT_PUBLIC_API_URL=http://api:8000 \
  --build-arg NEXT_PUBLIC_WS_URL=ws://api:8000 \
  -t atlas-ai-frontend .

# Run
docker run -p 3000:3000 atlas-ai-frontend
```

## Key Features

- **Dashboard** — Live incident summary, severity breakdown, service health overview
- **Incidents** — Filterable list (severity, status, search), paginated grid
- **Incident Detail** — One-click investigation trigger, real-time WebSocket agent progress feed
- **RCA Report** — Section-navigable report: executive summary, timeline, root cause, contributing factors, fix recommendations, lessons learned, PDF export
- **Agents** — All 9 agent types with status, metrics, success rate
- **Learning** — Accuracy trend (Recharts line chart), outcome distribution bar chart, agent performance, approved resolution history
- **Dark theme** — Full dark UI with Tailwind + CSS variables
