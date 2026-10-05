'use client';
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="error-page"><h1>The city needs a moment.</h1><p>Your recording is preserved. Try loading the view again.</p><button onClick={reset}>Reload view</button></main>;
}
