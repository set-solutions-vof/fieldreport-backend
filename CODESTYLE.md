# CODESTYLE

## 1. Purpose

This document defines the coding standard for Python backend projects and AI coding agents.

It is a reusable rulebook for implementation work. It defines required defaults, forbidden patterns, and preferred ways to structure, test, and validate Python service code.

## 2. Core Principles

Code MUST optimize for readability at the point of change.

Python MUST be used as a design tool, not as a place for loose, untyped scripting.

Public contracts MUST be designed first, with internal logic kept independent from transport and framework details.

API transport, orchestration, domain transformation, security, configuration, and integration concerns MUST be separated into distinct layers.

Changes MUST stay small, local, and easy to review.

Existing project patterns MUST be reused before new patterns are introduced.

Code MUST follow KISS, YAGNI, DRY, and SOLID.

Code MUST NOT include redundant functions, speculative abstractions, or defensive branches for impossible states.

Code MUST use clear variable and function names.

Code MUST NOT add comments or docstrings unless the project explicitly requires that convention.

Functions SHOULD separate logical steps with a single blank line.

## 3. Project Structure Guidelines

Application entry files MUST act as composition layers.

Entry files MUST NOT contain large amounts of business logic, transport logic, or reusable domain transformation code.

Transport entrypoints such as HTTP routes, RPC handlers, background job handlers, or tool registrations MUST remain thin orchestration layers.

Use-case orchestration SHOULD live in dedicated service modules or an equivalent application layer.

External integrations such as API clients, SDK wrappers, storage gateways, or message bus adapters MUST live outside transport entrypoints.

Transport models, internal models, and public response models SHOULD remain separate when they serve different contracts.

Configuration access MUST be centralized in a dedicated configuration boundary.

Security and authentication concerns SHOULD live in their own layer rather than being scattered through feature modules.

Utility modules MUST stay narrowly scoped and MUST NOT become dumping grounds for unrelated helpers.

Tests SHOULD mirror source ownership boundaries so it is obvious which module is responsible for which behavior.

Generated outputs, deployment manifests, and environment-specific assets MUST stay outside the application source layer.

When a module does not have a clear ownership boundary, it SHOULD be moved or split before more code is added to it.

## 4. Python and Typing Rules

Required Rules

The project MUST use modern Python typing features appropriate to its supported version.

Code SHOULD use built-in generics and PEP 604 unions when the supported Python version allows them.

Public function signatures, method signatures, and return values MUST be typed.

Untyped `dict`, `list`, and `tuple` usage MUST NOT be introduced at module boundaries when a concrete shape is known.

Boundary contracts MUST use explicit typed models or typed data structures.

Nullability MUST be expressed explicitly in types.

Optional fields MUST only be used when absence is part of the contract.

Type assertions and casts MUST be minimized and kept at the narrowest possible boundary.

Runtime shape conversion MUST happen immediately at the transport or integration boundary.

Preferred Conventions

Types SHOULD be named after domain meaning, not transport trivia.

Transport models SHOULD stay separate from internal models and public response models when those layers have different responsibilities.

Shared contracts SHOULD only be centralized when multiple modules truly depend on them.

Inference MAY be used for obvious local variables, but public contracts SHOULD remain explicit.

Module-level constants SHOULD use clear uppercase names.

## 5. Transport and Entrypoint Rules

Transport entrypoints MUST act as orchestration layers.

Transport entrypoints MUST NOT contain business logic, domain transformation logic, or external integration logic.

Transport entrypoints MUST translate incoming requests into service calls and translate service results into transport responses.

Framework-specific concerns MUST stay in transport modules.

Shared use-case behavior across multiple entrypoints MUST be implemented in service or lower layers, not duplicated per entrypoint.

If a framework exposes native validation or response contracts, those primitives SHOULD be used consistently at the boundary.

## 6. Service Layer Rules

Service classes or equivalent application-layer modules MUST orchestrate collaborators and assemble the final use-case result.

A service MUST NOT own transport details that belong in clients or gateways.

A service MUST NOT own framework concerns that belong in entrypoints.

Services SHOULD depend on internal models and response contracts, not on raw payload dictionaries.

If a service method starts mixing orchestration with transport parsing or framework behavior, it SHOULD be split.

## 7. Integration and Client Rules

Network, storage, and third-party integration access MUST be centralized in dedicated client or gateway modules.

Integration modules MUST own request construction, sessions or connections, headers or credentials, endpoint or query construction, and transport response validation.

Integration modules MUST return typed models or typed values, not raw unvalidated payloads.

Modules outside the integration layer MUST NOT construct transport-specific requests ad hoc.

Environment-specific endpoints, credentials, and runtime configuration MUST come from the configuration boundary, not hard-coded values.

## 8. Model and Contract Rules

Typed models MUST be the source of truth at module boundaries.

Internal models MUST remain independent from framework classes and external payload shapes.

Request and response models MUST represent the public contract only.

Transport models MUST reflect the external system payload shape only.

Internal domain rules MUST NOT leak into transport model modules.

If two layers need similar models for different reasons, they SHOULD remain separate unless the contract is truly identical.

## 9. Configuration and Environment Rules

Environment access MUST be centralized in a dedicated configuration module or boundary.

Modules MUST NOT scatter environment reads across the codebase.

Secrets MUST NOT be committed.

Example environment files SHOULD exist when local configuration is required.

Configuration fields MUST be typed.

Runtime configuration MUST be injected from configuration values, not hard-coded in feature modules.

## 10. Error Handling Rules

Errors MUST be handled at the layer that owns the concern.

Transport-level status mapping MUST stay in transport modules.

Integration failures MAY propagate when that matches the current public behavior and error contract.

Code MUST NOT add speculative fallback branches for states the system contract says cannot happen.

Errors MUST NOT be swallowed silently.

User-facing responses SHOULD be explicit when authentication, authorization, validation, or request handling fails.

## 11. Function and Class Design Rules

Each function and class MUST have one primary responsibility.

Methods SHOULD stay small enough that orchestration steps are obvious without extra explanation.

Class names MUST use PascalCase.

Functions, methods, variables, and module names MUST use clear snake_case names.

A file SHOULD export one primary responsibility when practical.

Repeated logic SHOULD be extracted only when the duplication is real and stable.

Boolean mode explosions SHOULD be avoided. If many flags are needed to express behavior, the design SHOULD be split.

## 12. Testing Rules

Every project MUST expose standard commands for formatting, linting, static analysis, testing, and running the service when those tools exist.

Behavior changes MUST include test changes unless the project has an explicit documented exception.

Tests MUST verify the responsibility of the module under test.

Tests MUST mock collaborators at the boundary touched by the module under test.

Tests MUST NOT re-test the internals of dependencies already covered elsewhere.

Entrypoint tests SHOULD verify transport behavior and orchestration.

Service tests SHOULD verify orchestration across mocked collaborators.

Integration client tests SHOULD verify request behavior and boundary parsing against mocked transports.

Domain transformation, security, and utility tests SHOULD verify only that layer’s responsibility.

Test names SHOULD describe the scenario and expected outcome.

Tests SHOULD be realistic and focused rather than optimized for artificial coverage numbers.

## 13. Imports, Exports, and Module Boundaries

Imports MUST flow inward toward more stable and shared layers.

Shared modules MUST NOT import from entrypoints, feature shells, or application bootstraps.

Feature or transport-specific code MUST NOT leak into shared internal layers.

Circular dependencies MUST NOT be introduced.

Imports SHOULD stay readable and grouped consistently.

If a module starts importing across unrelated feature boundaries, ownership is probably wrong and SHOULD be corrected.

## 14. Dependency Rules

Before adding a dependency, existing standard library modules and current project libraries MUST be checked first.

A new dependency MUST NOT duplicate existing project capability without a deliberate replacement decision.

New dependencies SHOULD be evaluated for maintenance cost, API complexity, operational impact, and fit with the current architecture.

New frameworks for routing, configuration, validation, persistence, or background execution MUST NOT be introduced casually into an established codebase.

When a dependency is added, the reason SHOULD be documented in the change description or project documentation.

## 15. AI Coding Agent Rules

Agents MUST inspect nearby code, project scripts, and configuration before editing.

Agents MUST follow existing local patterns unless there is a clear defect or explicit instruction to change them.

Agents MUST prefer minimal changes over broad rewrites.

Agents MUST reuse existing services, models, configuration access, and testing patterns before creating new abstractions.

Agents MUST NOT invent new architecture to solve a local problem.

Agents MUST NOT edit generated files, deployment outputs, or build artifacts directly.

Agents MUST update or add tests when behavior changes.

Agents MUST manually validate changes by running the relevant code path or a temporary debug script when feasible.

Agents MUST run relevant repository validation commands when feasible.

Agents MUST state what they validated and what they did not validate.

When the rulebook is silent, agents SHOULD follow the nearest stable local pattern.

When the codebase is inconsistent, agents SHOULD choose the safer maintainable pattern and call out the inconsistency in handoff.

## 16. Before Starting Work Checklist

Read `CODESTYLE.md`.

Read repository-specific instructions such as `AGENTS.md`.

Inspect project scripts and dependency configuration.

Inspect lint, formatter, type-check, test, and build configuration.

Read nearby modules in the same layer.

Identify the owning layer for the requested change.

Check whether a service, model, validator, client, gateway, or security helper already exists for the responsibility.

Check how configuration and environment values are accessed.

Check whether any target file is generated, environment-specific, or deployment-only.

Identify the validation commands relevant to the change.

## 17. Before Submitting Work Checklist

Run formatting checks relevant to the change.

Run lint.

Run static analysis if the project exposes it.

Run tests relevant to the change.

Run the changed code path manually or through a temporary debug script when feasible.

Review the change for duplicated logic.

Review the change for boundary violations between transport, service, integration, and model layers.

Confirm that no generated or deployment files were edited manually unless explicitly required.

Summarize the change and validation results clearly.

## 18. Generalized Recipes

Adding a New Endpoint or Handler

Define or reuse typed request and response contracts.

Keep the entrypoint thin.

Delegate behavior to a service or lower layer.

Keep transport-specific error mapping in the transport layer.

Add entrypoint-level tests.

Adding a New Service Method

Start from the public contract outward.

Orchestrate existing collaborators before introducing new abstractions.

Keep transport details in clients or gateways.

Return a typed result that matches the owning boundary.

Add focused service tests with mocked collaborators.

Adding a New Integration Call

Add the request in the owning client or gateway module.

Model the response at the integration boundary.

Validate transport data at the boundary.

Consume the result through a service or domain transformation layer, not directly from entrypoints.

Add integration client tests.

Adding or Updating Domain Transformation

Translate transport or persistence models into internal models only.

Keep transformation logic free of framework and transport-call side effects.

Add tests that verify transformation behavior at that boundary.

Adding or Updating Security Behavior

Keep authentication, authorization, and credential handling in the security layer.

Return typed results or explicit failures rather than leaking framework-specific behavior into lower layers.

Add focused tests for the security layer’s responsibility.

Refactoring Duplicated Logic

Confirm that the duplication is real and stable.

Extract to the narrowest shared layer that preserves ownership boundaries.

Update callers incrementally.

Re-run validation after the extraction.

## 19. Adaptation Notes

Apply these rules through the framework and tooling the project actually uses.

If a project intentionally departs from a rule, that exception SHOULD be explicit and documented.

When project conventions conflict with this file, the team SHOULD either update this file or document the local exception near the conflicting rule.
