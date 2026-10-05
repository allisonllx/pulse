import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'Pulse — The internet, from everywhere.',
  description: 'Explore geographically sampled public internet surfaces through topic storefronts, country comparisons, and a replayable recording.'
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
