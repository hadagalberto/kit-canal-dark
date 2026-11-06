import { Composition, registerRoot } from "remotion";
import { defaultProps, storyMetadata } from "../../news/story";
import { FPS, HEIGHT, WIDTH } from "../../timing";
import { Reel } from "./Reel";

/** Entry with only this style, so a broken neighbor style never blocks the render. */
const Root = () => (
  <Composition
    id="Estilo-Vidro"
    component={Reel}
    defaultProps={defaultProps}
    calculateMetadata={storyMetadata}
    durationInFrames={defaultProps.story.timing.total}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);

registerRoot(Root);
