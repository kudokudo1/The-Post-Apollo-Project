import {register} from "node:module";
register(new URL("./write_cli_loader.mjs", import.meta.url), import.meta.url);
