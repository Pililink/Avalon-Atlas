<script lang="ts">
  import SearchBox from "./components/SearchBox.svelte";
</script>

<main class="container">
  <h1>Avalon Atlas</h1>
  <p class="subtitle">极速地图查询工具</p>
  
  <SearchBox />
</main>

<style>
  .container {
    margin: 0;
    padding-top: 5vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
  }

  h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    background: linear-gradient(45deg, #4ecdc4, #556270);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .subtitle {
    color: #888;
    margin-bottom: 2rem;
  }
</style>
