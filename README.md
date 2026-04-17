# UncleGoWhere

UncleGoWhere is an agentic travel buddy built as a Cloud Computing (`SC4052`) project. It is a modular travel-planning assistant based on OpenClaw, designed around a multi-agent architecture where specialist agents handle flights, stays, itinerary generation, reviews, profile management, and response rewriting.

The system is intended to demonstrate Personal Assistant-as-a-Service (`PAaaS`) ideas in a travel domain. User requests are routed through a central orchestrator, which coordinates the relevant agents and returns a consolidated response through Telegram.

## What This Project Includes

- A multi-agent travel assistant workspace built on OpenClaw
- Specialist travel agents for flight search, accommodation search, itinerary planning, and related support tasks
- A Telegram-facing layer for chat-based interaction
- Supporting configuration, prompts, and skill definitions for local or cloud deployment

## Project Focus

UncleGoWhere was developed to explore:

- modular agent orchestration
- API-driven travel services
- Telegram-based user interaction
- deployment of an OpenClaw-based assistant on AWS

## Repository Structure

- `openclaw-workspace/` - main workspace, agent docs, and skills
- `tripclaw/` - model/config-related assets

## Notes

This repository accompanies the project report and presentation slides, which contain the full architecture, design rationale, implementation details, evaluation, and limitations. The README is intentionally brief.
