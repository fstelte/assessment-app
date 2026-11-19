# Release notes: BIA component modal edit link (2026.10.4)

## What's new

- **Edit from the component modal works again.** On the BIA edit page
  (`/bia/item/<id>/edit`), clicking a component opens its modal. Its **Edit**
  button went to `/bia/component//edit<id>/edit` and showed an error page. It
  now opens the component's edit page.
- All four URLs in that modal are built the same way. The last `/0` path
  segment of each `url_for` template is replaced with the component id, so
  links work whether the id is at the end or in the middle of the path. This
  also works behind a reverse proxy with a path prefix.

## Who can do what

Nothing changes.

## Behaviour changes to be aware of

None. This restores the intended behaviour. The bug came in with commit
`95b1895`.

## Upgrade

No database migration, settings or environment variables.

## Known limitations and follow-ups

None.
