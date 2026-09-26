# Group mode

Use groups only for a coherent collection the user wants presented together.
A parent and every child have their own `full.md`, `summary.md` and source. The
parent has `doc_type: parent` plus `children: [child_one, child_two]`; each child
has `doc_type: child` and `parent: group_slug`. All share the category path.

```text
category/README.md
category/group_slug/full.md
category/group_slug/summary.md
category/group_slug/overview.md
category/group_slug/child_one/full.md
category/group_slug/child_one/summary.md
category/group_slug/child_one/source.pdf
```

The parent is a document, so do not put README.md inside it. Preserve original
filenames per child. If a group has no original parent source, write a clearly
self-authored `overview.md` and use that as the parent's source; do not pretend
it is an external source. Parent and child links should be explicit and relative.

Extract and review each input independently. A batch is not automatically a
group. Show the entire target tree and links for review. Validate the assembled
draft tree and every target before filing, then validate every filed document.
Catalog the collection in a way that keeps both the overview and children findable.
