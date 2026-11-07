// The generator page compiles weights of your own here, off the page's thread, so it can be stopped.
import { compileCustom } from "./compile.mjs";

onmessage = (e) => {
  try {
    postMessage({ result: compileCustom(e.data) });
  } catch (err) {
    postMessage({ error: err instanceof RangeError ? `The pattern would be ${err.message}.` : String(err.message ?? err) });
  }
};
