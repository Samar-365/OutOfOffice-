import { isEmpty } from 'lodash';
import { unusedHelper } from './utils';

export function add(a: number, b: number): number {
  return a + b;
}

export function multiply(a: number, b: number): number {
  return a * b;
}

// Dead function never referenced
export function deadLegacyFunction(data: any): boolean {
  console.log("This function is obsolete and should be pruned");
  return isEmpty(data);
}

// Unused private helper
function privateUnreachableRoutine(): string {
  return "unreachable";
}
