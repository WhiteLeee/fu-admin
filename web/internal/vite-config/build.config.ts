import { defineBuildConfig } from 'unbuild';

export default defineBuildConfig({
  clean: true,
  entries: ['src/index'],
  declaration: true,
  failOnWarn: false,
  rollup: {
    emitCJS: true,
  },
});
