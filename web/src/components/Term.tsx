import { define } from "@/lib/glossary";

/** Wraps a technical term with a plain-language tooltip from the glossary. */
export function Term({ k, children }: { k: string; children: React.ReactNode }) {
  const definition = define(k);
  if (!definition) {
    return <>{children}</>;
  }
  return (
    <span className="term" data-tip={definition}>
      {children}
    </span>
  );
}
