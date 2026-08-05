import Head from "next/head";
import Link from "next/link";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Head>
        <title>Dark Pool Intelligence Engine</title>
      </Head>
      <header className="topbar">
        <Link href="/" className="brand">
          Dark Pool Intelligence Engine
        </Link>
        <nav>
          <Link href="/">Overview</Link>
          <Link href="/tape">Tape</Link>
          <Link href="/backtest">Backtest</Link>
        </nav>
      </header>
      <main className="container">{children}</main>
      <footer className="footer">
        Probabilities, not promises — nothing here is financial advice. Check
        the invalidation levels before acting on anything.
      </footer>
    </>
  );
}
