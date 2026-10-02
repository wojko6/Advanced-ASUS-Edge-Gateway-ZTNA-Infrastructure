# RouterCloud deployed frontend baseline

This directory preserves the sanitized frontend state captured from the
deployed RouterCloud service on 2026-10-02.

It is the compatibility baseline for the RouterCloud Metro Web redesign.

The current deployed frontend already differs from stock Dufs 0.46.0 and
contains project-specific behavior including:

- Polish localization;
- RouterCloud branding;
- storage usage presentation;
- a separate allow_move capability;
- rename constrained to the current parent directory;
- collision rejection instead of overwrite;
- DELETE visibility controlled independently by backend capability.

The rendered runtime directory data was removed before publication.

Captured asset hashes:

- index.css: b18caf9e126489e3a4cdc99817818c0560e70c079d5025ea1052a6d6b285c123
- index.js: c767bc884a65fca5baf4b5c4745af81c2f365d7dd0433d8c4178ca13eed1d54e
- favicon.ico: 092a155f9ba0dad3b38591bbc1b7185c74c7bec19892c895c01dddee6cf9fca7

Do not edit this baseline when implementing Metro UI. Copy from it into the
active frontend and keep this directory as a regression reference.
