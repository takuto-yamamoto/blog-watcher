# ADR-004: Deployment Approach

## Status

Accepted

## Decision

Docker-based deployment using a multi-stage build approach with docker-compose orchestration.

### Dockerfile Strategy

**Multi-stage build:**
- Builder stage: Install dependencies with gcc/libxml2
- Runtime stage: Slim image, non-root user, health check

### Docker Compose Configuration

- Mount `config.yaml` as read-only
- Volume for SQLite database persistence
- Environment variables for secrets
- Resource limits (256MB memory, 0.5 CPU)
- Health check endpoint on port 8080

## Context

The application needs to be easily deployable in containerized environments with minimal configuration overhead while maintaining security best practices and resource efficiency.
