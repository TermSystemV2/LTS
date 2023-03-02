<template>
	<div>
		<el-drawer
			v-model="table"
			:title="drawerTitle"
			direction="rtl"
			size="50%"
		>
			<el-table :data="gridData">
			<el-table-column property="grade" label="Grade" width="150" />
			<el-table-column property="class" label="Class" width="200" />
			<el-table-column property="name" label="Name" />
			</el-table>
		</el-drawer>
		<div class="container">
			<div class="handle-box">
				<el-select v-model="term" placeholder="请选择学期" class="handle-select mr10" @change="$forceUpdate()">
					<el-option key="11" label="第一学年·第一学期" value="11"></el-option>
					<el-option key="12" label="第一学年·第二学期" value="12"></el-option>
					<el-option key="21" label="第二学年·第一学期" value="21"></el-option>
					<el-option key="22" label="第二学年·第二学期" value="22"></el-option>
					<el-option key="31" label="第三学年·第一学期" value="31"></el-option>
					<el-option key="32" label="第三学年·第二学期" value="32"></el-option>
					<el-option key="41" label="第四学年·第一学期" value="41"></el-option>
					<el-option key="42" label="第四学年·第二学期" value="42"></el-option>
				</el-select>
				<el-button type="primary" :icon="Search" @click="handleSearchTerm(term)">搜索</el-button>
			</div>
			<div class="handle-box">
				<el-select v-model="courseName" placeholder="请选择课程"  clearable class="handle-select mr10"
				@change="$forceUpdate()" @clear="clearCourses">
					<el-option v-for="course in coursesData" :key="course.label" :value="course.value">
					</el-option>
				</el-select>
				<el-button type="primary" :icon="Search" @click="handleSearchCourse(courseName)">搜索</el-button>
				<!-- <el-button type="primary" :icon="Plus">新增</el-button> -->
			</div>
			<div class="quickCourses">
				<el-radio-group v-model="radioCourse" @change="chooseCourse">
					<el-radio :label="course.label" v-for="course in coursesData"
					:key="course.label" class="myradio">{{course.value}}</el-radio>
				</el-radio-group>
			</div>
			<div>
				<el-table :data="tableData" border class="table" ref="multipleTable" header-cell-class-name="table-header"
				:row-style="{height: '500px'}" :header-cell-style="{textAlign: 'center'}" :cell-style="{ textAlign: 'center' }">
				<!-- <el-table-column prop="id" label="ID" width="55" align="center"></el-table-column> -->
				<el-table-column prop="courseName" label="课程名称" width="140">
					<template #default="scope">
						{{scope.row.courseName}}
						<p class="fail_text">（共计{{scope.row.sumFailedNums}}人次）</p>
						<el-button type="primary" bg @click="openDrawer(scope.row.courseName)">挂科学生详情</el-button>
					</template>
				</el-table-column>
				<el-table-column label="考试通过情况">
					<template #default="scope">
						<CourseBar :chartData="scope.row" />
					</template>
				</el-table-column>
				<el-table-column label="分数分段情况">
					<template #default="scope">
						<CourseLine :chartData="scope.row" />
					</template>
				</el-table-column>
				<!-- <el-table-column label="头像(查看大图)" align="center">
					<template #default="scope">
						<el-image
							class="table-td-thumb"
							:src="scope.row.thumb"
							:z-index="10"
							:preview-src-list="[scope.row.thumb]"
							preview-teleported
						>
						</el-image>
					</template>
				</el-table-column>
				<el-table-column prop="address" label="地址"></el-table-column>
				<el-table-column label="状态" align="center">
					<template #default="scope">
						<el-tag
							:type="scope.row.state === '成功' ? 'success' : scope.row.state === '失败' ? 'danger' : ''"
						>
							{{ scope.row.state }}
						</el-tag>
					</template>
				</el-table-column>

				<el-table-column prop="date" label="注册时间"></el-table-column>
				<el-table-column label="操作" width="220" align="center">
					<template #default="scope">
						<el-button text :icon="Edit" @click="handleEdit(scope.$index, scope.row)" v-permiss="15">
							编辑
						</el-button>
						<el-button text :icon="Delete" class="red" @click="handleDelete(scope.$index)" v-permiss="16">
							删除
						</el-button>
					</template>
				</el-table-column> -->
			</el-table>
		</div>
		</div>

		<!-- 编辑弹出框 -->
		<!-- <el-dialog title="编辑" v-model="editVisible" width="30%">
			<el-form label-width="70px">
				<el-form-item label="用户名">
					<el-input v-model="form.name"></el-input>
				</el-form-item>
				<el-form-item label="地址">
					<el-input v-model="form.address"></el-input>
				</el-form-item>
			</el-form>
			<template #footer>
				<span class="dialog-footer">
					<el-button @click="editVisible = false">取 消</el-button>
					<el-button type="primary" @click="saveEdit">确 定</el-button>
				</span>
			</template>
		</el-dialog> -->
	</div>
</template>

<script setup lang="ts" name="basetable">
import { ref, reactive, onMounted } from 'vue';
import { ElDrawer,ElMessage, ElMessageBox } from 'element-plus';
import { Delete, Edit, Search, Plus } from '@element-plus/icons-vue';
import { fetchData, fetchCoursesData } from '../api/index';
import CourseBar from "../components/courseBar.vue";
import CourseLine from '../components/courseLine1.vue';

interface TableItem {
	courseName: string;
	failed_nums: string;
	gradeDistribute: string;
	id: string;
	pass_rate: string;
	sumFailedNums: string;
}
interface ListItem {
  value: string
  label: string
}

const query = reactive({
	address: '',
	name: '',
	pageIndex: 1,
	pageSize: 10
});
let term = '11'
const radioCourse = ref("");
const courseName = ref("");
const tableData = ref<TableItem[]>([]);
const tableDataCopy = ref<TableItem[]>([]);
let coursesData = ref<ListItem[]>([]);

const table = ref(false)
const drawerTitle = ref("");
const gridData = [
  {
    grade: '21级',
    class: '2103班',
    name: '陈阵阳',
  },
  {
    grade: '22级',
    class: '2208班',
    name: '王文婕',
  },
  {
    grade: '22级',
    class: '2208班',
    name: '刘夕源',
  },
  {
    grade: '22级',
    class: '2208班',
    name: '周佳',
  },
]

onMounted(() => {
	getData(term);
})
// 获取表格数据
const getData = (term: String) => {
	// fetchData().then(res => {
	// 	tableData.value = res.data.list;
	// 	pageTotal.value = res.data.pageTotal || 50;
	// 	console.log(tableData.value);
	// });
	fetchCoursesData(term).then(res => {
		courseName.value = "";
		tableData.value = [];
		tableDataCopy.value = res.data.data;
		console.log(tableDataCopy.value);
		coursesData.value = [];
		for(var key in tableDataCopy.value){
			coursesData.value.push({
				value: tableDataCopy.value[key].courseName,
				label: tableDataCopy.value[key].courseName
			})
		}
		// console.log(coursesData);
	});
};

// 查询操作
const handleSearchTerm = (term: String) => { // 根据学期搜索
	getData(term);
};
const handleSearchCourse = (courseName: String) => { // 根据课程名称搜索
	// console.log('course:' + courseName);
	// console.log(tableData.value);
	// console.log(tableDataCopy.value);
	console.log(courseName);
	radioCourse.value = "";
	
	tableData.value = tableDataCopy.value;
	tableData.value = tableData.value.filter((item) => {
        return item.courseName == courseName
    })
};
const clearCourses = () => { // 清除所选课程
	// console.log(tableDataCopy.value);
	// radioCourse.value = "";
	// tableData.value = [];
}

const chooseCourse = () => { // 选择某个课程
	console.log(radioCourse.value);
	// showTable.value = true;
	courseName.value = "";
	tableData.value = tableDataCopy.value;
	tableData.value = tableData.value.filter((item) => {
        return item.courseName == radioCourse.value
    })
}

const openDrawer = (val:string) => { // 点击打开抽屉
	table.value = true;
	console.log(val);
	drawerTitle.value = "《"+val+"》挂科同学详情";
}

// // 删除操作
// const handleDelete = (index: number) => {
// 	// 二次确认删除
// 	ElMessageBox.confirm('确定要删除吗？', '提示', {
// 		type: 'warning'
// 	})
// 		.then(() => {
// 			ElMessage.success('删除成功');
// 			tableData.value.splice(index, 1);
// 		})
// 		.catch(() => {});
// };

// // 表格编辑时弹窗和保存
// const editVisible = ref(false);
// let form = reactive({
// 	name: '',
// 	address: ''
// });
// let idx: number = -1;
// const handleEdit = (index: number, row: any) => {
// 	idx = index;
// 	form.name = row.name;
// 	form.address = row.address;
// 	editVisible.value = true;
// };
// const saveEdit = () => {
// 	editVisible.value = false;
// 	ElMessage.success(`修改第 ${idx + 1} 行成功`);
// 	tableData.value[idx].name = form.name;
// 	tableData.value[idx].address = form.address;
// };
</script>

<style scoped>
.handle-box {
	display: inline-block;
	margin-bottom: 20px;
	margin-right: 50px;
}

.handle-select {
	width: 200px;
}

.handle-input {
	width: 300px;
}

.table {
	width: 100%;
	font-size: 14px;
}

.red {
	color: #ff0000;
}

.mr10 {
	margin-right: 10px;
}

.table-td-thumb {
	display: block;
	margin: auto;
	width: 40px;
	height: 40px;
}

.fail_text {
	color: #ff0000;
	font-size: 10px;
}
.myradio {
	width: 25%;
}
</style>
