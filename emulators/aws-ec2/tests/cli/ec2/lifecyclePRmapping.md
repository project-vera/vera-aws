## Summary

This PR adds three EC2 lifecycle test cases under `emulators/aws-ec2/tests/cli/ec2/`:

- `subnet-lifecycle.rst`
- `internet-gateway-lifecycle.rst`
- `route-table-lifecycle.rst`

These cases extend the existing lifecycle-style coverage already present in files such as:

- `vpc-lifecycle.rst`
- `volume-lifecycle.rst`
- `vpc-endpoint-lifecycle.rst`

## Why

The current EC2 CLI corpus already contains the atomic building blocks for these workflows, but the lifecycle validation is still fragmented across separate create / describe / delete examples.

This PR groups those existing assets into complete lifecycle-oriented flows so that the test corpus can validate:

- parent resource setup
- resource creation
- state and relationship verification via describe calls
- cleanup ordering

## Mapping from existing cases

| Existing `.rst` set | Lifecycle-related? | Missing steps / gaps | Resulting lifecycle flow |
|---|---|---|---|
| `create-subnet.rst` + `describe-subnets.rst` + `delete-subnet.rst` | Yes, partial | missing parent VPC setup, wait step, and grouped cleanup | create-vpc → wait → create-subnet → describe-subnets → delete-subnet → delete-vpc |
| `create-internet-gateway.rst` + `attach-internet-gateway.rst` + `describe-internet-gateways.rst` + `detach-internet-gateway.rst` + `delete-internet-gateway.rst` | Yes, partial | missing parent VPC setup, wait step, and grouped attach/detach cleanup flow | create-vpc → wait → create-internet-gateway → attach → describe-internet-gateways → detach → delete-internet-gateway → delete-vpc |
| `create-route-table.rst` + `describe-route-tables.rst` + `delete-route-table.rst` | Yes, partial | missing parent VPC setup, wait step, and grouped cleanup | create-vpc → wait → create-route-table → describe-route-tables → delete-route-table → delete-vpc |

## Notes

- The new files follow the existing lifecycle file style already used in `vpc-lifecycle.rst`.
- These cases intentionally use a minimal workflow slice and do not yet add extra mutation steps such as subnet attribute modification, route association flows, or route creation via internet gateway.
- The goal of this PR is to establish the smallest clear lifecycle assets first, then extend coverage incrementally if needed.