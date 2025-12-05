# Docker Quick Start Guide

## Prerequisites
- Docker Desktop installed on Windows
- Docker daemon running

## Build and Run

### Option 1: Run the full pipeline
```bash
docker-compose up --build
```

### Option 2: Run Kedro Viz
```bash
docker-compose up viz
```
Then open http://localhost:4141 in your browser.

### Option 3: Interactive shell
```bash
docker-compose run rosetta bash
```

## Common Commands

```bash
# Build image only
docker-compose build

# Run specific pipeline
docker-compose run rosetta kedro run --pipeline=data_processing

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v
```

## Data Persistence

The `data/` directory is mounted as a volume, so:
- Downloaded Wiktionary dumps persist between runs
- Generated outputs are saved to your local filesystem
- You can inspect results directly in `data/` folder

## Troubleshooting

**Build fails**: Ensure Docker Desktop is running
**Port already in use**: Change port in docker-compose.yml
**Permission errors**: Run Docker Desktop as administrator
