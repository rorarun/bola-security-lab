# Approved permission matrix

Normative policy implemented by M2 endpoint-specific authorization. Roles apply per project,
with no implicit organization administrator. Baseline and centralized comparisons are deferred.

| Action | Owner | Editor | Viewer | Same-org nonmember | Cross-org outsider |
|---|---|---|---|---|---|
| Read project | Allow | Allow | Allow | Deny | Deny |
| List/read project tasks | Allow | Allow | Allow | Deny | Deny |
| Create task | Allow | Allow | Deny | Deny | Deny |
| Update task content/status | Allow | Allow | Deny | Deny | Deny |
| Delete task | Allow | Deny | Deny | Deny | Deny |
| Update/delete project | Allow | Deny | Deny | Deny | Deny |
| Read membership list | Allow | Deny | Deny | Deny | Deny |
| Add existing organization member | Allow | Deny | Deny | Deny | Deny |
| Change/remove non-owner membership | Allow | Deny | Deny | Deny | Deny |
| Remove/demote/replace owner | Deny | Deny | Deny | Deny | Deny |

- Organization creation establishes creator membership; registration alone creates no tenant rights.
- Organization metadata and project creation require organization membership.
- Organization lists show joined organizations. Project lists show only joined projects.
- Project creation and sole owner membership are atomic; ownership transfer is out of scope.
- Task creator identity grants no extra permissions. Editors can update any task in their project.
- Owners may add only existing members of the same organization.
- Complete organization/project/task paths must agree. Bodies cannot reassign tenant, project or creator.
- Revocation/downgrade applies to requests starting after commit, even with an unexpired session.
  Overlapping requests require separate concurrency guarantees and tests.
- Project deletion may cascade to children; owner removal while retaining the project is prohibited.

Response contract: invalid authentication `401`; absent or outside-readable-scope object `404`;
readable project but insufficient action role `403`; invalid body `422`; membership/owner conflict
`409`. Authorized lists return `200` and exactly the permitted records, including empty lists.
