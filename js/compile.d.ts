export interface CustomOptions {
  /** Weights, repeating; the first applies to the rightmost digit (from: "right") or the leftmost. */
  weights: number[];
  /** The weighted sum must be 0 modulo this (default 10). */
  mod?: number;
  from?: "left" | "right";
  /** A fixed number of digits, or null for any number (default). */
  length?: number | null;
  /** Give up on regexes longer than this many characters (default: no limit). */
  budget?: number;
}

export interface Compiled {
  pattern: string;
  length: number;
  /** One per prime power of the modulus: its regex's length and the construction that won. */
  components: Record<string, { length: number; construction: string; tried: Record<string, number | null> }>;
}

/** The pattern `rexsum custom` prints for the same options, character for character. */
export declare function compileCustom(options: CustomOptions): Compiled;

/** An <input> element for a pattern, as `rexsum … --html` prints it; `attrs` go before the pattern. */
export declare function inputElement(pattern: string, attrs?: string): string;
