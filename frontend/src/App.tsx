import { useState } from "react";

import { projectApi } from "./api/client";
import { ProjectView } from "./components/ProjectView";
import { StudioForm } from "./components/StudioForm";
import type { CreateProjectInput, Project } from "./types";

export default function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function createProject(payload: CreateProjectInput) {
    setLoading(true);
    setError(null);
    try {
      setProject(await projectApi.create(payload));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-mist text-ink">
      <div className="pointer-events-none fixed inset-0 opacity-60 [background-image:radial-gradient(circle_at_20%_5%,rgba(109,93,252,0.2),transparent_28%),radial-gradient(circle_at_90%_25%,rgba(91,214,178,0.18),transparent_25%)]" />
      <div className="relative mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <header className="mx-auto mb-10 max-w-2xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white bg-white/70 px-3 py-1.5 text-xs font-semibold text-zinc-600 shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Creative workspace
          </div>
          <h1 className="text-4xl font-semibold tracking-[-0.04em] text-ink sm:text-6xl">AI Video Studio</h1>
          <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-zinc-500 sm:text-base">
            Shape your concept into a scene-by-scene production plan, ready for the generation pipeline.
          </p>
        </header>

        <div className="mx-auto max-w-3xl">
          <StudioForm loading={loading} onSubmit={createProject} />
          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {error}
            </div>
          )}
        </div>

        {project && <ProjectView project={project} />}
      </div>
    </main>
  );
}
