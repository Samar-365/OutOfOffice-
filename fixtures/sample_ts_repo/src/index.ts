import { add, multiply } from './math';
import { formatOutput } from './utils';

export function main() {
  const sum = add(5, 10);
  const prod = multiply(2, 4);
  console.log(formatOutput(sum + prod));
}
