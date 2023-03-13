<template>
	<div class="container">
		<el-switch
			v-model="switchData"
			class="ml-2"
			size="large"
			active-text="从原始数据中读取"
			inactive-text="从计算结果中读取"
			@change="changeSwitch"
		/>
		<!-- <div class="content-title">支持拖拽</div>
		<div class="plugins-tips">
			Element Plus自带上传组件。 访问地址：
			<a href="https://element-plus.org/zh-CN/component/upload.html" target="_blank">Element Plus Upload</a>
		</div> -->
		<!-- <el-upload class="upload-demo" drag action="http://jsonplaceholder.typicode.com/api/posts/" multiple :on-change="handle">
			<el-icon class="el-icon--upload"><upload-filled /></el-icon>
			<div class="el-upload__text">
				将文件拖到此处，或
				<em>点击上传</em>
			</div>
			<template #tip>
				<div class="el-upload__tip">只能上传 jpg/png 文件，且不超过 500kb</div>
			</template>
		</el-upload> -->
		<el-upload
			class="upload-demo"
			drag
			:action="actionUrl"
			:auto-upload="false"
			v-model:file-list="fileList"
			multiple
			ref="uploadRef"
		>
			<el-icon class="el-icon--upload"><upload-filled /></el-icon>
			<div class="el-upload__text">
			将文件拖到此处，或<em>点击上传</em>
			</div>
			<template #tip>
			<div class="el-upload__tip">
				<!-- 只能上传 jpg/png 文件，且不超过 500kb -->
				上传的文件列表如下：
			</div>
			</template>
		</el-upload>
		<el-button class="ml-3" type="success" @click="submitUpload">
		确定上传
		</el-button>

		<!-- <div class="content-title">支持裁剪</div>
		<div class="plugins-tips">
			vue-cropperjs：一个封装了 cropperjs 的 Vue 组件。 访问地址：
			<a href="https://github.com/Agontuk/vue-cropperjs" target="_blank">vue-cropperjs</a>。 示例请查看
			<router-link to="/user">个人中心</router-link>
		</div> -->
	</div>
</template>

<script setup lang="ts">
import { fi } from "element-plus/es/locale";
import {ref, onMounted} from "vue"
import type { UploadUserFile, UploadRawFile, UploadInstance  } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Action } from 'element-plus'
import {toRaw} from '@vue/reactivity'
import {uploadFile, updateState, getState} from '../api/index'

const fileList = ref<UploadUserFile[]>([])
const switchData = ref(true)
const stateStr = ref<string>("")
const actionUrl = ref<string>("proxy/apis/v1/uploadfile/");
const uploadRef = ref<UploadInstance>()

onMounted(() => {
	getDataWay('read_from_origin');
})

const handle = (rawFile:any)=>{
	console.log(rawFile);
}

const submitUpload = () => { // 确定上传按钮点击事件
	console.log(fileList.value);
	let fileNames:string = "";
	fileList.value.forEach((el:any) => {
		fileNames += '<p>' + el.name + '</p>';
	})
	fileNames += '<p>'+"确定上传这些文件吗？"+'</p>';
	console.log(fileNames);
	ElMessageBox.confirm(
		fileNames,
		'上传文件',
		{
		confirmButtonText: '确认',
		cancelButtonText: '取消',
		dangerouslyUseHTMLString: true,
		}
	).then(() => {
		uploadRef.value!.submit();
		ElMessage({
			type: 'success',
			message: '文件上传成功！',
		})
		uploadRef.value!.clearFiles();
	}).catch(() => {
		ElMessage({
			type: 'info',
			message: '取消上传文件！',
		})
    })
}

// 调用修改数据读取方式的接口
const updateDataWay = (name: string) => {
	updateState(name).then(res => {
		if (res.data.code == '200' || res.data.code == 200) {
			let data = res.data.data;
			console.log(data);
			if (data.state) {
				stateStr.value = "从原始数据中读取";
			} else {
				stateStr.value = "从计算结果中读取";
			}
			console.log(stateStr.value);
		} else {
			console.log('updateState接口请求不成功！');
		}
	})
}

// 调用读取数据读取方式的接口
const getDataWay = (name:string) => {
	getState(name).then(res => {
		if (res.data.code == '200' || res.data.code == 200) {
			let data = res.data.data;
			// console.log(data);
			if (data.state) {
				stateStr.value = "从原始数据中读取";
				switchData.value = true;
			} else {
				stateStr.value = "从计算结果中读取";
				switchData.value = false;
			}
			console.log(switchData.value);
		} else {
			console.log('getState接口请求不成功！');
		}
	})
}

// 切换switch开关，控制数据读取方式
const changeSwitch = (val:boolean) => {
	console.log(val);
	if (val) { // 从原始数据中读取
		updateDataWay('read_from_origin');
	} else { // 从计算结果中读取
		updateDataWay('read_from_origin');
	}
}
</script>

<style scoped>
.content-title {
	font-weight: 400;
	line-height: 50px;
	margin: 10px 0;
	font-size: 22px;
	color: #1f2f3d;
}

.pre-img {
	width: 100px;
	height: 100px;
	background: #f8f8f8;
	border: 1px solid #eee;
	border-radius: 5px;
}
.crop-demo {
	display: flex;
	align-items: flex-end;
}
.crop-demo-btn {
	position: relative;
	width: 100px;
	height: 40px;
	line-height: 40px;
	padding: 0 20px;
	margin-left: 30px;
	background-color: #409eff;
	color: #fff;
	font-size: 14px;
	border-radius: 4px;
	box-sizing: border-box;
}
.crop-input {
	position: absolute;
	width: 100px;
	height: 40px;
	left: 0;
	top: 0;
	opacity: 0;
	cursor: pointer;
}
</style>
