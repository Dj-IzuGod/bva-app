/**
 * ImageUploadTile -- reusable file-pick / drag-drop tile for the Score page.
 *
 * Controlled + presentational: the PARENT owns the File and its preview URL;
 * this tile renders the preview (or the empty state) and reports user intent
 * upward via onSelect / onClear. Reused twice (Image A / Image B).
 */

import { useRef, useState } from "react";

export default function ImageUploadTile({
  label,
  file,
  previewUrl,
  disabled = false,
  onSelect,
  onClear,
}) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  /** Filter dropped/picked files down to a single image. */
  function handleFiles(fileList) {
    const picked = fileList && fileList[0];
    if (picked && picked.type.startsWith("image/")) onSelect(picked);
  }

  return (
    <div className="flex flex-col">
      <span className="mb-2 text-sm font-medium text-slate-600">{label}</span>

      <div
        role="button"
        tabIndex={0}
        aria-label={`Upload ${label}`}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (!disabled) handleFiles(e.dataTransfer.files);
        }}
        className={[
          "relative flex h-56 items-center justify-center overflow-hidden",
          "rounded-xl border-2 border-dashed transition-colors cursor-pointer",
          dragOver ? "border-teal-600 bg-teal-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100",
          disabled ? "opacity-50 pointer-events-none" : "",
        ].join(" ")}
      >
        {previewUrl ? (
          <>
            <img src={previewUrl} alt={`${label} preview`} className="h-full w-full object-contain" />
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onClear(); }}
              className="absolute top-2 right-2 rounded-full bg-slate-900/70 px-2 py-0.5 text-xs text-white hover:bg-slate-900"
            >
              Remove
            </button>
          </>
        ) : (
          <div className="px-4 text-center">
            <p className="text-sm font-medium text-slate-500">Click or drop an image here</p>
            <p className="mt-1 text-xs text-slate-400">JPG, PNG, BMP or WebP</p>
          </div>
        )}
      </div>

      {file && (
        <p className="mt-1 truncate text-xs text-slate-500" title={file.name}>
          {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB
        </p>
      )}

      {/* Hidden native input does the actual file picking. */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }}
      />
    </div>
  );
}
