import mediaTypes from '../fileexplorer/media_types.json';

const textExtensions = new Set(`txt text log cfg conf config ini inf properties prop env
json jsonc json5 jsonl ndjson geojson yaml yml toml xml xsd xsl xslt xaml plist vdf vmt vtf.txt acf manifest
md markdown mdown mkd mdx rst adoc asciidoc org tex bib sty cls rtf csv tsv tab srt vtt ass ssa lrc cue m3u m3u8 pls
sh bash zsh fish ksh csh bashrc zshrc profile ps1 psm1 psd1 bat cmd py pyi pyw rb rake gemspec pl pm lua luau tcl awk sed
js jsx mjs cjs ts tsx mts cts css scss sass less html htm xhtml svelte vue astro php phtml sql graphql gql proto
c h cc hh cpp hpp cxx hxx cs fs fsx vb java kt kts scala go rs swift m mm r rmd jl dart ex exs erl hrl hs lhs clj cljs cljc edn
pas pp d zig nim v vala asm s inc glsl vert frag geom tesc tese comp hlsl shader compute gd gdshader unity tscn tres godot
cmake make mk mak gradle groovy sum mod lock nix desktop service socket timer target mount automount path scope slice rules udev
reg urls url webloc gitignore gitattributes gitmodules gitconfig editorconfig dockerignore npmrc nvmrc yarnrc browserslistrc
htaccess htoprc inputrc nanorc vimrc wgetrc curlrc screenrc tmux.conf desktop.in desktop.template pot po svg diff patch pem crt cer pub asc
tf tfvars hcl dockerfile containerfile ipynb ipynb.txt spec recipe bb bbappend bbclass sdl ansible inventory hosts fstab`.split(/\s+/));
const textNames = new Set(`readme license licence copying copyright notice authors contributors changelog changes news todo install
makefile gnumakefile bsdmakefile cmakelists.txt dockerfile containerfile vagrantfile gemfile rakefile procfile brewfile justfile
jenkinsfile meson.build meson_options.txt configure config .env .profile .bashrc .bash_profile .bash_logout .zshrc .zprofile
.gitignore .gitattributes .gitmodules .gitconfig .editorconfig .dockerignore .npmrc .yarnrc .nvmrc .vimrc .nanorc .tmux.conf
hosts hostname fstab resolv.conf passwd group shadow`.split(/\s+/));

export const isImage = (name: string) => /\.(bmp|png|apng|jpe?g|jpe|jfif|gif|webp)$/i.test(name);
export const isArchive = (name: string) => /\.(zip|rar|7z|tar|gz|bz2|xz|tgz|tbz2?|txz)$/i.test(name);
export function mediaType(name: string): string | undefined {
  return (mediaTypes as Record<string, string>)[name.toLowerCase().split('.').pop() || ''];
}
export function isText(name: string): boolean {
  const lower = name.toLowerCase();
  return textNames.has(lower) || textExtensions.has(lower.split('.').pop() || '') ||
    /^(readme|licen[cs]e|copying|changelog|authors|notice)(\.[\w-]+)?$/.test(lower) ||
    /^\.env(\.[\w.-]+)?$/.test(lower) || /^(dockerfile|containerfile)(\.[\w-]+)?$/.test(lower);
}
export function openKind(entry: { name: string; directory: boolean; link: boolean }) {
  if (entry.directory) return 'folder';
  if (entry.link) return null;
  if (isImage(entry.name)) return 'image';
  if (isArchive(entry.name)) return 'archive';
  if (mediaType(entry.name)) return 'media';
  if (isText(entry.name)) return 'text';
  return null;
}
