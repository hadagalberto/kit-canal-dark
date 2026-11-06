import { Composition } from "remotion";
import { defaultProps, storyMetadata } from "./news/story";
import { Reel as Vidro } from "./styles/vidro/Reel";
import { FPS, HEIGHT, WIDTH } from "./timing";

/**
 * Os estilos do kit. Vem um só de exemplo (vidro): cada canal deve criar o seu visual a partir
 * de src/styles/DESIGN-TEMPLATE.md, para não sair igual a outros canais feitos com o kit.
 * Cada estilo renderiza uma `Story` (pacote da notícia + tempos medidos + marca) passada com --props;
 * a duração vem da história. O render de produção usa o entry.tsx do próprio estilo
 * (scripts/render-style.mjs). Esta Root é para o Studio. Estilo novo: importe e acrescente aqui.
 */
const styles = [{ id: "Estilo-Vidro", component: Vidro }];

export const RemotionRoot = () => {
  return (
    <>
      {styles.map((style) => (
        <Composition
          key={style.id}
          id={style.id}
          component={style.component}
          defaultProps={defaultProps}
          calculateMetadata={storyMetadata}
          durationInFrames={defaultProps.story.timing.total}
          fps={FPS}
          width={WIDTH}
          height={HEIGHT}
        />
      ))}
    </>
  );
};
