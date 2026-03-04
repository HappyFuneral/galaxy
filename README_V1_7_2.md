# V1.7.2 – Save recipe overrides + HQ re-export

## New endpoints
- PATCH /exports/{job_id}/{export_id}/recipe
- POST  /exports/{job_id}/{export_id}/reexport
- GET   /exports/{job_id}/files/{name}

## Notes
- Re-export is synchronous in this version.
  If it becomes slow, the next iteration can queue it as a background job.
