# Security evidence

The repository generates software-supply-chain evidence in a dedicated GitHub
Actions workflow without adding security tools to Raspberry Pi runtime
dependencies.

## Workflow

The `Security Evidence` workflow runs on:

- pull requests;
- pushes to `main`;
- semantic-version tags;
- manual dispatch.

For each run it uploads a `security-evidence-<commit>` artifact.

## SBOM

The workflow generates:

```text
security-evidence/sbom.cdx.json
```

using CycloneDX JSON from the Poetry project and lockfile, including all
application extras.

The SBOM generation uses reproducible-output mode and validates the generated
CycloneDX document.

The security tooling version is pinned separately in
`requirements-security.txt`; it is not part of the runtime Poetry dependency
graph.

## Dependency audit

The workflow installs the application with all optional extras, captures the
exact installed dependency set, and audits those versions with `pip-audit`.

Artifacts include:

```text
security-evidence/installed-requirements.txt
security-evidence/pip-audit.json
security-evidence/pip-audit-exit-code.txt
```

## Current enforcement policy

A vulnerability finding is **evidence, not an automatic merge failure**.

`pip-audit` exit code 1 means known vulnerabilities were reported. The
workflow converts that result into a GitHub Actions warning and still uploads
the complete JSON report for review.

Execution/tooling failures remain blocking. For example, if the audit cannot
run, the report cannot be generated, or the SBOM generator fails validation,
the Security Evidence workflow fails.

This distinction prevents an unreviewed advisory from silently blocking every
repository change while still making findings visible and downloadable.

## Reviewing findings

For each reported vulnerability:

1. confirm the affected package/version is actually present in the installed
   environment;
2. identify whether the vulnerable functionality is reachable in this project;
3. check whether a fixed version is compatible with the current dependency
   graph;
4. record any accepted risk or false-positive rationale in the relevant issue;
5. update dependencies and regenerate evidence when remediation is available.

Do not suppress findings solely to make CI green.

## Release evidence

Semantic-version tag pushes also run the Security Evidence workflow. This means
a release commit has both:

- validated Python release artifacts from the `Release` workflow;
- an SBOM and vulnerability-audit artifact from the `Security Evidence`
  workflow.

The SBOM/audit files are workflow artifacts rather than GitHub Release
attachments for now. Signing/attestation policy can be added separately if the
repository later needs stronger supply-chain guarantees.
