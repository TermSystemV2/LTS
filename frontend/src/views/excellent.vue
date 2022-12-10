<template>
	<div class="container">
		<div class="plugins-tips">
			优良学风班情况
		</div>
		<div class="schart-box">
			<div class="content-title">优良学风班数量及比例</div>
			<ExcellentBar />
		</div>
		<div class="schart-box">
			<div class="content-title">各年级优良学风班比例</div>
			<ExcellentLine />
		</div>
	</div>
</template>

<script setup lang="ts" name="basecharts">
import ExcellentBar from "../components/excellentBar.vue";
import ExcellentLine from "../components/excellentLine.vue";

</script>

<style scoped>
.container{
	width: 100%;
	height: 70%;
}
.schart-box {
	display: inline-block;
	width: 50%;
	height: 100%;
}

.schart {
	width: 600px;
	height: 400px;
}

.content-title {
	clear: both;
	font-weight: 400;
	line-height: 50px;
	margin: 10px 0;
	margin-left: 10px;
	font-size: 22px;
	color: #1f2f3d;
}
</style>
