# Additional modes

These are natural-language agent workflows, not flags on one monolithic script.
The workspace rules and existing authorization apply in every mode.

## Check

Run the selected backend's doctor, inspect the catalog, run `kb.py tree`, and
validate affected documents with `--filed`. Report actual failures; do not modify
content during a read-only check. Check source hashes/coverage separately when
requested because structural validation cannot measure factual completeness.

## Batch

Inventory all configured supported inputs. Preserve each source's identity;
extract and draft each independently, then present one consolidated filing plan.
Avoid interleaving two writing agents. Workers run sequentially, one image each.
Authentication/quota failures stop that backend's run. Resume from verified cache;
`--force` intentionally re-spends calls. Never silently drop a failed document.

## Delete

Identify the exact documents, incoming links, catalog and category changes. Ask
only for deletion authorization that is not already present. Back up affected
metadata, move documents into timestamped recoverable `TRASH_DIR`, then update
links/catalog and revalidate. Do not use permanent recursive deletion for this.

## Teach

Draft a source-backed explanation or guide from identified material. Keep factual
claims linked to source documents and distinguish newly authored teaching text.
If it becomes a new KB document, create an explicit self-authored source and follow
the normal review/filing process. Teaching does not authorize unrelated edits.
