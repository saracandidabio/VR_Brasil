# Publicação completa no GitHub — VR_Brasil

Dashboard: **https://vrbrasil.streamlit.app/**  
Repositório: **https://github.com/saracandidabio/VR_Brasil**

## Substituir todos os arquivos versionados de uma vez (recomendado)

**Não exclua o repositório nas configurações do GitHub.** Substitua os arquivos em um único commit e mantenha a implantação do Streamlit vinculada ao mesmo endereço. A operação a seguir remove os arquivos **da versão atual**, mas **não apaga o histórico dos commits**.

1. Descompacte `VR_Brasil_Completo_Atualizado.zip`, obtendo a pasta `VR_Brasil_pronto` (caso o Mac acrescente um sufixo, ajuste o nome no comando de cópia).
2. No Terminal, abra a pasta em que você extraiu o ZIP. Por exemplo, se estiver em **Downloads**:

```bash
cd ~/Downloads
git clone https://github.com/saracandidabio/VR_Brasil.git VR_Brasil_publicacao
cd VR_Brasil_publicacao
```

3. **No clone recém-criado**, confira a pasta:

```bash
git remote -v
git branch --show-current
```

A resposta deve indicar `saracandidabio/VR_Brasil` e `main`. Não continue se o repositório for outro.

4. Apague de uma vez os arquivos versionados **dentro desse clone**, mantendo o repositório `.git` e seu histórico:

```bash
git rm -r -- .
```

5. Copie o conteúdo **interno** da pasta nova, incluindo `.streamlit/` e `.gitignore`:

```bash
cp -R ../VR_Brasil_pronto/. .
```

6. Confira o estado antes de publicar:

```bash
python3 validar_publicacao.py
git add -A
git status
```

Verifique que `data/` contém os 8 cubos, os 4 pares de complementos de Centro-Oeste e os GeoJSON; não deve aparecer `.venv/`, `downloads_srag/` nem CSVs brutos.

7. Envie a substituição em um único commit:

```bash
git commit -m "Consolida observatorio SRAG com mapas e dados MT-MS"
git push origin main
```

O Streamlit Community Cloud deve reconstruir o app conectado à branch `main` e ao arquivo `streamlit_app.py`. Pode ser necessário abrir a página do aplicativo para conferir o resultado. O pacote foi validado localmente, mas a publicação remota depende do seu acesso ao GitHub.

## Não quer remover tudo?

Em um repositório já clonado, é possível copiar apenas os arquivos novos por cima dos antigos e executar `git add -A`, `git commit` e `git push`. No seu caso, a substituição limpa evita deixar arquivos de versões anteriores.

## Erros frequentes

- `fatal: destination path ... already exists`: escolha um outro nome, como `VR_Brasil_publicacao_2`, e ajuste o `cd`.
- `git: command not found`: instale as ferramentas de linha de comando do Xcode (`xcode-select --install`).
- `Permission denied (publickey)` ou erro de autenticação HTTPS: autentique-se no GitHub com uma credencial adequada (GitHub CLI, gerenciador de credenciais ou token). Nunca compartilhe senhas ou tokens.
- Se o `git push` reclamar que a branch não é `main`, confira `git branch --show-current` antes de tentar outro nome.
- **Não use `git push --force`** para substituir arquivos, não é necessário.
- Excluir arquivos do commit atual **não remove cópias do histórico Git**. Para retirar conteúdo sensível previamente exposto, é necessário tratar o histórico separadamente.

> Alternativa no site: é possível excluir arquivos e pastas pela interface do GitHub, mas para dezenas de arquivos a substituição via Git é mais adequada e mantém o histórico em um único commit.
