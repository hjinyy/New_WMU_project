# MATPOWER public benchmark source manifest (v4)

These files are verbatim public case definitions copied from the MATPOWER repository for reproducibility of the **benchmark-proxy** audit only:

- `case14.m` — https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case14.m
  SHA-256 `2ffc4e1b734ae6c5e92dbe68b4e36010ed695a4bbcc4d065c74c4fbc39fcf3c1`
- `case30.m` — https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case30.m
  SHA-256 `3d9030311259b553be85d02336b7e1bcb24ec04775bee6671bdb62d18e4e2137`
- `case_ieee30.m` — https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case_ieee30.m
  SHA-256 `b3bcc6165577e9e70a39af98f808405233a184289056cab8ce35fbc5a3ad953e`

Upstream project/license/reference: https://github.com/MATPOWER/matpower . This vendoring does not claim that these cases are the source system used to generate the raw WMU waveforms. For v4 role labeling, `case30` is the primary **simplified/OPF-style IEEE30 proxy** because the local diagnostic matches its 100-MVA base and checked loads; `case_ieee30` is a secondary CDF-fidelity sensitivity case. Neither role validates individual electrical parameters or transient behavior.
