export const comparisonLimit = 3;

export function comparisonPath(ids) {
  const params = new URLSearchParams();
  for (const id of ids) params.append('config', id);
  return `/compare/${params.size ? `?${params}` : ''}`;
}
