# Versionamento — Saga Engine

Adotar SemVer: MAJOR.MINOR.PATCH

Significado:
- MAJOR: mudanças incompatíveis na API pública (editor/runtime).
- MINOR: novas features compatíveis retroativamente.
- PATCH: correções, pequenos ajustes e docs.

Processo de release (resumido)
1. Atualizar `docs/CHANGELOG.md` sob a seção "Unreleased" com as mudanças.
2. Bump da versão no arquivo `shared/VERSION`.
   - Ex.: atualizar de 0.1.0 para 0.2.0
   - Commit: "chore(release): bump version to X.Y.Z"
3. Tag no Git: `git tag -a vX.Y.Z -m "Release X.Y.Z"`
4. Push: `git push origin main --tags`
5. Criar Release no GitHub usando a tag e o changelog.

Checklist de pré-release
- [ ] Todos os testes rodam e estão verdes.
- [ ] Lint/format aplicado (black/isort/ruff).
- [ ] CHANGELOG atualizado.
- [ ] Build/pack (se aplicável) gerado e verificado.

Branches e fluxo (simplicado)
- main: código estável e liberado.
- develop: integração contínua das features prontas.
- feature/*: desenvolvimento isolado.
- release/*: preparação de release (opcional).
- hotfix/*: correções urgentes aplicadas a main.

Comandos úteis
- Bump versão manual:
  - Editar shared/VERSION
  - git add shared/VERSION; git commit -m "chore(release): bump version to X.Y.Z"
- Criar tag assinado simples:
  - git tag -a vX.Y.Z -m "Release vX.Y.Z"
  - git push origin vX.Y.Z

Política de compatibilidade
- Documentar breaking changes em CHANGELOG sob a seção "Breaking Changes".
- APIs públicas definidas em docs/API.md (criar quando necessário).
