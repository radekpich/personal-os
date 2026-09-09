export function czechPlural(count: number, one: string, few: string, many: string) {
  const abs = Math.abs(count);
  if (abs === 1) return one;
  if (abs >= 2 && abs <= 4) return few;
  return many;
}

export function formatCzechCount(count: number, one: string, few: string, many: string) {
  return `${count} ${czechPlural(count, one, few, many)}`;
}
