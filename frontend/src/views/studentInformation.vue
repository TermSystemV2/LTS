<template>
	<div>
		<div class="container">
			<div class="handle-box">
				<el-select v-model="grade" placeholder="请选择年级" class="handle-select mr10" @change="$forceUpdate()">
					<el-option key="18" label="2018级" value="18"></el-option>
					<el-option key="19" label="2019级" value="19"></el-option>
					<el-option key="20" label="2020级" value="20"></el-option>
					<el-option key="21" label="2021级" value="21"></el-option>
				</el-select>
				<el-button type="primary" :icon="Search" @click="handleSearchTerm(grade)">搜索</el-button>
			</div>
			<div class="handle-box">
				<el-input v-model="studentID" placeholder="请输入学号" class="handle-input mr10"></el-input>
				<el-input v-model="studentName" placeholder="请输入姓名" class="handle-input mr10"></el-input>
				<el-button type="primary" :icon="Search" @click="handleSearchStudent(studentID,studentName)">查询</el-button>
				<!-- <el-button type="primary" :icon="Plus">新增</el-button> -->
			</div>
			<el-row v-for="(item, index) in tableData">
				<el-col>
					<!-- :data里需要是个数组 所以这里将item用[]进行包裹-->
					<el-table :data="[item]" border class="table" ref="multipleTable"
						header-cell-class-name="table-header" :row-style="{ height: '10px' }"
						:header-cell-style="{ textAlign: 'center' }" :cell-style="{ textAlign: 'center' }">
						<!-- <el-table-column prop="id" label="ID" width="55" align="center"></el-table-column> -->
						<el-table-column prop="index" label="序号" width="120">
						</el-table-column>
						<el-table-column prop="stuID" label="学号" width="120">
						</el-table-column>
						<el-table-column prop="stuName" label="姓名" width="120">
						</el-table-column>
						<el-table-column prop="stuClass" label="班级" width="120">
						</el-table-column>
						<el-table-column prop="totalWeightedScore" label="加权平均" width="120">
						</el-table-column>
						<el-table-column prop="failedSubjectNums" label="累计不及格科目数" width="140">
						</el-table-column>
						<el-table-column prop="sumFailedCredit" label="累计不及格学分" width="150">
						</el-table-column>
						<el-table-column prop="failedSubjectNames" label="不及格科目具体名称" :show-overflow-tooltip="true">
						</el-table-column>
					</el-table>
					<el-table :data="[item]" border class="table" ref="multipleTable"
						header-cell-class-name="table-header" :row-style="{ height: '500px' }"
						:header-cell-style="{ textAlign: 'center' }" :cell-style="{ textAlign: 'center' }">
						<el-table-column prop="totalWeightedScoreTerm,failedSubjectNumsTerm" label="个人成绩柱状图">
							<template #default="scope" class="template">
								<StudentInfoBar
									:chartData="{ totalWeightedScoreTerm: scope.row.totalWeightedScoreTerm, failedSubjectNumsTerm: scope.row.failedSubjectNumsTerm }" />
							</template>
						</el-table-column>
						<el-table-column prop="selfContent" label="个人分析">
							<el-card>
								<template #header>
									<div class="card-header">
										<span>第一学年个人分析</span>
									</div>
								</template>
								<div class="text item">个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析</div>
							</el-card>
							<el-card>
								<template #header>
									<div class="card-header">
										<span>第二学年个人分析</span>
									</div>
								</template>
								<div class="text item">个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析</div>
							</el-card>
							<el-card>
								<template #header>
									<div class="card-header">
										<span>第三学年个人分析</span>
									</div>
								</template>
								<div class="text item">个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析</div>
							</el-card>
							<el-card>
								<template #header>
									<div class="card-header">
										<span>第四学年个人分析</span>
									</div>
								</template>
								<div class="text item">个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析个人分析</div>
							</el-card>
						</el-table-column>
					</el-table>
				</el-col>
			</el-row>

			<div class="pagination">
				<el-pagination background layout="total, prev, pager, next" :current-page="query.pageIndex"
					:page-size="query.pageSize" :total="pageTotal" @current-change="handlePageChange"></el-pagination>
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
import { ref, reactive } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete, Edit, Search, Plus, User } from '@element-plus/icons-vue';
import { fetchStudntInfoData } from '../api/index';
import type { TableColumnCtx } from 'element-plus/es/components/table/src/table-column/defaults'
import StudentInfoBar from '../components/studentInfoBar.vue';

interface TableItem {
	stuID: string
	stuName: string
	stuClass: string
	term1: object
	term2: object
	term3: object
	term4: object
	totalWeightedScore: number
	totalWeightedScoreTerm1: number
	totalWeightedScoreTerm2: number
	totalWeightedScoreTerm3: number
	totalWeightedScoreTerm4: number
	failedSubjectNamesScores: object
	failedSubjectNames: string
	failedSubjectNums: number
	sumFailedCredit: number
	failedSubjectNumsTerm: number[]
	totalWeightedScoreTerm: number[]
	selfContent: object
	index: number
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
let grade = '18'
let studentID = ''
let studentName = ''
const tableData = ref<TableItem[]>([]);
const tableDataCopy = ref<TableItem[]>([]);
let coursesData = ref<ListItem[]>([]);
const pageTotal = ref(0);
// 获取表格数据
const getData = (grade: String) => {
	// fetchData().then(res => {
	// 	tableData.value = res.data.list;
	// 	pageTotal.value = res.data.pageTotal || 50;
	// 	console.log(tableData.value);
	// });
	fetchStudntInfoData(grade).then(res => {
		tableData.value = res.data.data;
		tableDataCopy.value = tableData.value;
		console.log(tableData.value);
	});
};
getData(grade);

// 查询操作
const handleSearchTerm = (grade: String) => {
	query.pageIndex = 1;
	console.log('term:' + grade);
	getData(grade);
};
const handleSearchStudent = (studentID: String,studentName:String) => {
	console.log('studentID:' + studentID);
	console.log('studentName:' + studentName);
	tableData.value = tableDataCopy.value;
	tableData.value = tableData.value.filter((item) => {
		return item.stuID == studentID && item.stuName == studentName
	})
};
// 分页导航
const handlePageChange = (val: number) => {
	query.pageIndex = val;
	getData(grade);
};

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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text {
	font-size: 14px;
}

.item {
	padding: 8px 0;
}

</style>
