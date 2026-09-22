import { Clock3, Image, MoreHorizontal, Play, WandSparkles } from "lucide-react";

import type { Project } from "../types";

interface ProjectViewProps {
  project: Project;
}

function label(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function ProjectView({ project }: ProjectViewProps) {
  return (
    <section className="mt-10 animate-[fadeIn_500ms_ease-out]">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-electric">
            <WandSparkles size={14} /> Project
          </div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Production plan</h2>
        </div>
        <span className="w-fit rounded-full bg-amber-100 px-3 py-1.5 text-xs font-semibold text-amber-800">
          {label(project.status)}
        </span>
      </div>

      <div className="rounded-[2rem] border border-white/80 bg-white/80 p-6 shadow-soft backdrop-blur sm:p-8">
        <dl className="grid gap-6 border-b border-zinc-200 pb-7 md:grid-cols-[2fr_1fr_1fr]">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Prompt</dt>
            <dd className="mt-2 max-w-3xl text-sm leading-6 text-zinc-700">{project.prompt}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Duration</dt>
            <dd className="mt-2 text-sm font-semibold text-ink">{project.duration_seconds} seconds</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Quality</dt>
            <dd className="mt-2 text-sm font-semibold capitalize text-ink">{project.quality}</dd>
          </div>
        </dl>

        <div className="mb-5 mt-7 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-ink">Scenes</h3>
            <p className="mt-1 text-xs text-zinc-500">{project.scenes.length} clips in the initial timeline</p>
          </div>
          <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-500">
            ~5s each
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {project.scenes.map((scene) => (
            <article
              className="group overflow-hidden rounded-2xl border border-zinc-200 bg-white transition hover:-translate-y-0.5 hover:border-zinc-300 hover:shadow-lg"
              key={scene.id}
            >
              <div className="relative grid aspect-video place-items-center bg-gradient-to-br from-zinc-100 to-zinc-200 text-zinc-400">
                <Image size={25} strokeWidth={1.5} />
                <button
                  aria-label={`Preview scene ${scene.order}`}
                  className="absolute grid h-10 w-10 place-items-center rounded-full bg-white/90 text-ink opacity-0 shadow-md transition group-hover:opacity-100"
                  disabled
                  type="button"
                >
                  <Play fill="currentColor" size={15} />
                </button>
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-ink">Scene {String(scene.order).padStart(2, "0")}</h4>
                    <p className="mt-1 flex items-center gap-1.5 text-xs text-zinc-500">
                      <Clock3 size={12} /> {scene.duration_seconds} seconds
                    </p>
                  </div>
                  <MoreHorizontal className="text-zinc-400" size={18} />
                </div>
                <div className="mt-4 flex items-center gap-2 text-xs">
                  <span className="h-2 w-2 rounded-full bg-zinc-300" />
                  <span className="font-medium capitalize text-zinc-500">{scene.status}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
